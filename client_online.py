import tenseal as ts
from time import time
import socket,zlib
import pickle,rrokvs,mmh3
from math import log2
from parameters import  output_bits,plain_modulus, poly_modulus_degree, bin_capacity, alpha, ell, cuckoo_hash_seeds,VBF_hash_seeds,slice_number,dummy_msg_client,label_size
from cuckoo_hash import reconstruct_item, Cuckoo
from auxiliary_functions import windowing,split_integers_unique_first_block
from oprf import order_of_generator, client_prf_online_parallel,client_prf_offline, G

oprf_client_key = 12345678910111213141516171819222222222222
client_point_precomputed = (oprf_client_key % order_of_generator) * G
base = 2 ** ell
minibin_capacity = int(bin_capacity / alpha)
logB_ell = int(log2(minibin_capacity) / ell) + 1 # <= 2 ** HE.depth
table_size=2**output_bits
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('localhost', 4470))

# Setting the public and private contexts for the BFV Homorphic Encryption scheme
private_context = ts.context(ts.SCHEME_TYPE.BFV, poly_modulus_degree=poly_modulus_degree, plain_modulus=plain_modulus)
public_context = ts.context_from(private_context.serialize())
public_context.make_context_public()
client_set = []
with open('client_set.csv', 'r') as f:
    lines = f.readlines()
    for line in lines:
        item,label=line[:-1].split(",")
        binary_item = bin(int(item))[2:]
        binary_label = bin(int(label))[2:]
        for i in range(len(binary_label)):
            concat_binary_item = binary_item + str(int(binary_label[:i+1])^1)  
            decimal_value = int(concat_binary_item, 2)  
            client_set.append(decimal_value)
t0 = time()
encoded_client_set = [client_prf_offline(item, client_point_precomputed) for item in client_set]
# We prepare the partially OPRF processed database to be sent to the server
encoded_client_set_serialized = zlib.compress(pickle.dumps(encoded_client_set, protocol=pickle.HIGHEST_PROTOCOL))
L = len(encoded_client_set_serialized)
#将消息长度 L 转换为字符串，然后在字符串末尾填充空格，使其总长度为 10 字符。这种方法可以确保服务器可以准确地解析消息的长度。
sL = str(L) + ' ' * (10 - len(str(L)))
client_to_server_communiation_oprf = L #in bytes
# The length of the message is sent first
client.sendall(sL.encode())#编码为字节流
client.sendall(encoded_client_set_serialized)

#开始接受server处理过的oprf数据，即C=sB.其中s为发送方OPRF秘钥。client计算r^(-1)C=sA即可。
L = client.recv(10).decode().strip()
L = int(L, 10)
PRFed_encoded_client_set_serialized = b""
while len(PRFed_encoded_client_set_serialized) < L:
    data = client.recv(8192)
    if not data: break
    PRFed_encoded_client_set_serialized += data   
PRFed_encoded_client_set = pickle.loads(zlib.decompress(PRFed_encoded_client_set_serialized))

server_to_client_communication_oprf = len(PRFed_encoded_client_set_serialized)

# We finalize the OPRF processing by applying the inverse of the secret key, oprf_client_key
key_inverse = pow(oprf_client_key, -1, order_of_generator)
PRFed_client_set = client_prf_online_parallel(key_inverse, PRFed_encoded_client_set)
t1=time()
print('*OPRFphase time:{:.2f}s'.format(t1 - t0))
#VBF编码
VBF_PRF_link={} #将数据与VBF编码建立关系，方便定位数据
VBF_PRFed_client_set=set()
for item in PRFed_client_set:
    VBF_value=[mmh3.hash128(str(item), VBF_hash_seeds[i], signed=False) for i in range(2)]
    VBF_PRF_link[item]=VBF_value
    for i in range(2):
        VBF_PRFed_client_set.add(VBF_value[i])
t2=time()
print('*VBF phase time:{:.2f}s'.format(t2 - t1))
# Each PRFed item from the client set is mapped to a Cuckoo hash table
CH = Cuckoo(cuckoo_hash_seeds)
for item in VBF_PRFed_client_set:
    CH.insert(item)

# We padd the Cuckoo vector with dummy messages
for i in range(CH.number_of_bins):
    if (CH.data_structure[i] == None):
        CH.data_structure[i] = dummy_msg_client
t3=time()
print('*Cuckoo hashing time:{:.2f}s'.format(t3 - t2))
# We apply the windowing procedure for each item from the Cuckoo structure
windowed_items = []
dict_index_itemslice={}
item_slice_list=split_integers_unique_first_block(CH.data_structure,slice_number)#数据切片
for index,item in enumerate(CH.data_structure):
    dict_index_itemslice[index]=item_slice_list[index]
    windowed_items.append(windowing(item_slice_list[index][0], minibin_capacity, plain_modulus))#后续处理第一分片即可
    # windowed_items.append(windowing(item, minibin_capacity, plain_modulus))

plain_query = [None for k in range(len(windowed_items))]
enc_query = [[None for j in range(logB_ell)] for i in range(1, base)]

# We create the <<batched>> query to be sent to the server
# By our choice of parameters, number of bins = poly modulus degree (m/N =1), so we get (base - 1) * logB_ell ciphertexts
for j in range(logB_ell):
    for i in range(base - 1):
        if ((i + 1) * base ** j - 1 < minibin_capacity):
            for k in range(len(windowed_items)):
                plain_query[k] = windowed_items[k][i][j]
            enc_query[i][j] = ts.bfv_vector(private_context, plain_query)

enc_query_serialized = [[None for j in range(logB_ell)] for i in range(1, base)]
for j in range(logB_ell):
    for i in range(base - 1):
        if ((i + 1) * base ** j - 1 < minibin_capacity):
            enc_query_serialized[i][j] = enc_query[i][j].serialize()

context_serialized = public_context.serialize()
message_to_be_sent = [context_serialized, enc_query_serialized]
message_to_be_sent_serialized = zlib.compress(pickle.dumps(message_to_be_sent, protocol=pickle.HIGHEST_PROTOCOL))
t4 = time()
print("*Computing ciphertext time:{:.2f}s".format(t4 - t3))
L = len(message_to_be_sent_serialized)
sL = str(L) + ' ' * (10 - len(str(L)))
client_to_server_communiation_query = L 
#the lenght of the message is sent first
client.sendall((sL).encode())
# Now we send the message to the server
client.sendall(message_to_be_sent_serialized)
t5 = time()
print("*sendall data time:{:.2f}s".format(t5 - t4))

# The answer obtained from the server:
L = client.recv(10).decode().strip()
L = int(L, 10)
answer = b""
while len(answer) < L:
    data = client.recv(8192)
    if not data: break
    answer += data
server_to_client_query_response = len(answer) #bytes
# Here is the vector of decryptions of the answer
(ciphertexts,link_slice_matrix) = pickle.loads(zlib.decompress(answer))
t6=time()
print("*Received coefficients and okvs matrix sent by the server,time:{:.2f}s".format(t6 - t5))
decryptions = []
for ct in ciphertexts:
    decryptions.append(ts.bfv_vector_from(private_context, ct).decrypt())

link_slice_matrix_array=link_slice_matrix.toarray()
with open('client_set.csv', 'r') as g:
    client_set_entries = g.readlines()
client_intersection = []
VBF_PRFed_common_element_set=set()
for j in range(alpha):
    for i in range(table_size):
        # link_slice_matrix_ij=link_slice_matrix[f"{i}_{j}"]
        link_slice_matrix_ij=link_slice_matrix_array[3*(alpha*i+j):3*(alpha*i+j+1)].tolist()
        # link_slice_matrix_ij=link_slice_matrix[alpha*i+j].toarray().tolist()
        if decryptions[j][i] == 0:
            reconstruct_slice=[]
            for link_vec in link_slice_matrix_ij:
                first_slice=dict_index_itemslice[i][0]
                remain_slice=dict_index_itemslice[i][1:]
                reconstruct_slice.append(rrokvs.decode([first_slice],link_vec,minibin_capacity)[0])
            if(remain_slice==reconstruct_slice):#第2，3，...分片全部相等
                # The index i is the location of the element in the intersection
                # Here we recover this element from the Cuckoo hash structure
                VBF_PRFed_common_element = reconstruct_item(CH.data_structure[i], i, cuckoo_hash_seeds[CH.data_structure[i] % 4])
                VBF_PRFed_common_element_set.add(VBF_PRFed_common_element)
for key,value in VBF_PRF_link.items():
    if all(num in VBF_PRFed_common_element_set for num in value):  
        # 如果value中的两个整数都在VBF_PRFed_common_element_set中，则将key添加到结果列表中  
        index = PRFed_client_set.index(key)
        client_intersection.append(client_set_entries[int(index/label_size)][:-1])
t7=time()
print("*Decrypt data to obtain intersection results,time:{:.2f}s".format(t7 - t6))
h = open('intersection.csv', 'r')
real_intersection = [line[:-1] for line in h]
h.close()
print('*Intersection recovered correctly: {}'.format(set(client_intersection) == set(real_intersection)))
print('*Client ONLINE computation time {:.2f}s'.format(t4 - t0 + t7 - t6))
print('*Communication size:')
print('    ~ Client --> Server:  {:.2f} MB'.format((client_to_server_communiation_oprf + client_to_server_communiation_query )/ (2 ** 20)))
print('    ~ Server --> Client:  {:.2f} MB'.format((server_to_client_communication_oprf + server_to_client_query_response )/ (2 ** 20)))
client.close()


