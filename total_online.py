"""
This Python file does not use socket programming,
which can quickly verify the correctness of the solution.
Simultaneously able to obtain computation time and communication overhead
"""
import tenseal as ts
import pickle,zlib,mmh3,rrokvs
import numpy as np
from math import log2

from cuckoo_hash import reconstruct_item, Cuckoo
from parameters import label_size,plain_modulus,dummy_msg_client,cuckoo_hash_seeds,VBF_hash_seeds,bin_capacity, alpha, ell,output_bits,slice_number,poly_modulus_degree
from auxiliary_functions import power_reconstruct,windowing,split_integers_unique_first_block
from oprf import server_prf_online_parallel,order_of_generator, client_prf_online_parallel,client_prf_offline, G
from time import time

oprf_server_key = 1234567891011121314151617181920
oprf_client_key = 12345678910111213141516171819222222222222
client_point_precomputed = (oprf_client_key % order_of_generator) * G
base = 2 ** ell
table_size=2**output_bits
minibin_capacity = int(bin_capacity / alpha)
logB_ell = int(log2(minibin_capacity) / ell) + 1 # <= 2 ** HE.depth

with open('server_preprocessed.pkl', 'rb') as g:
    (poly_coeffs,link_slice_matrix) = pickle.load(g)

# For the online phase of the server, we need to use the columns of the preprocessed database
transposed_poly_coeffs = np.transpose(poly_coeffs).tolist() #数组转置

private_context = ts.context(ts.SCHEME_TYPE.BFV, poly_modulus_degree=poly_modulus_degree, plain_modulus=plain_modulus)
public_context = ts.context_from(private_context.serialize())
public_context.make_context_public()
client_set = []
# clientset_file='./datasets/client_mnist.csv'
# intersection_file='./datasets/intersection_mnist.csv'
clientset_file='./datasets/client_diabetes.csv'
intersection_file='./datasets/intersection_diabetes.csv'
# clientset_file='client_set.csv'
# intersection_file='intersection.csv'
with open(clientset_file, 'r') as f:
    lines = f.readlines()
    for line in lines:
        item,label=line[:-1].split(",")
        binary_item = bin(int(item))[2:]
        binary_label = "0"*(label_size-len(bin(int(label))[2:]))+bin(int(label))[2:]
        for i in range(len(binary_label)):
            concat_binary_item = binary_item + str(int(binary_label[:i+1])^1)  
            decimal_value = int(concat_binary_item, 2)  
            client_set.append(decimal_value)
t0 = time()
encoded_client_set = [client_prf_offline(item, client_point_precomputed) for item in client_set]
# We prepare the partially OPRF processed database to be sent to the server
encoded_client_set_serialized = zlib.compress(pickle.dumps(encoded_client_set, protocol=pickle.HIGHEST_PROTOCOL))
c2s_oprf_commu = len(encoded_client_set_serialized)
encoded_client_set = pickle.loads(zlib.decompress(encoded_client_set_serialized))

# The server computes (parallel computation) the online part of the OPRF protocol, using its own secret key
PRFed_encoded_client_set = server_prf_online_parallel(oprf_server_key, encoded_client_set)
PRFed_encoded_client_set_serialized = zlib.compress(pickle.dumps(PRFed_encoded_client_set, protocol=pickle.HIGHEST_PROTOCOL))
s2c_oprf_commu = len(PRFed_encoded_client_set_serialized)
PRFed_encoded_client_set = pickle.loads(zlib.decompress(PRFed_encoded_client_set_serialized))

key_inverse = pow(oprf_client_key, -1, order_of_generator)
PRFed_client_set = client_prf_online_parallel(key_inverse, PRFed_encoded_client_set)
t1=time()
print('*DH-OPRF time:{:.2f}s'.format(t1 - t0))
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
first_slice=[]
item_slice_list=split_integers_unique_first_block(CH.data_structure,slice_number)#数据切片
for index,item in enumerate(CH.data_structure):
    dict_index_itemslice[index]=item_slice_list[index]
    first_slice.append(item_slice_list[index][0])
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
enc_message_to_be_sent = [context_serialized, enc_query_serialized]
message_to_be_sent=(enc_message_to_be_sent,first_slice)
message_to_be_sent_serialized = zlib.compress(pickle.dumps(message_to_be_sent, protocol=pickle.HIGHEST_PROTOCOL))
t4 = time()
print("*Computing ciphertext time:{:.2f}s".format(t4 - t3))
c2s_query_commu = len(message_to_be_sent_serialized)
(enc_message_to_be_sent,first_slice) = pickle.loads(zlib.decompress(message_to_be_sent_serialized))

srv_context = ts.context_from(enc_message_to_be_sent[0])#只能加密的public_context
received_enc_query_serialized = enc_message_to_be_sent[1]#client发送的y的密文
received_enc_query = [[None for j in range(logB_ell)] for i in range(base - 1)]
for i in range(base - 1):
    for j in range(logB_ell):
        if ((i + 1) * base ** j - 1 < minibin_capacity):
            received_enc_query[i][j] = ts.bfv_vector_from(srv_context, received_enc_query_serialized[i][j])

# Here we recover all the encrypted powers Enc(y), Enc(y^2), Enc(y^3) ..., Enc(y^{minibin_capacity}), from the encrypted windowing of y.
# These are needed to compute the polynomial of degree minibin_capacity
all_powers = [None for i in range(minibin_capacity)]
for i in range(base - 1):
    for j in range(logB_ell):
        if ((i + 1) * base ** j - 1 < minibin_capacity):
            all_powers[(i + 1) * base ** j - 1] = received_enc_query[i][j]

for k in range(minibin_capacity):
    if all_powers[k] == None:
        all_powers[k] = power_reconstruct(received_enc_query, k + 1)
all_powers = all_powers[::-1]#翻转数组，y^b,...,y^2,y

# Server sends alpha ciphertexts, obtained from performing dot_product between the polynomial coefficients from the preprocessed server database and all the powers Enc(y), ..., Enc(y^{minibin_capacity})
srv_answer = []
for i in range(alpha):
    # the rows with index multiple of (B/alpha+1) have only 1's
    dot_product = all_powers[0]
    for j in range(1,minibin_capacity):
        dot_product = dot_product + transposed_poly_coeffs[(minibin_capacity + 1) * i + j] * all_powers[j]
    dot_product = dot_product + transposed_poly_coeffs[(minibin_capacity + 1) * i + minibin_capacity]
    srv_answer.append(dot_product.serialize())
# The answer to be sent to the client is prepared
# data_to_client=(srv_answer,link_slice_matrix)
link_slice_matrix_array=link_slice_matrix.toarray()
reconstruct_slices=[[None for _ in range(alpha)] for _ in range(table_size)]
for j in range(alpha):
    for i in range(table_size):
        link_slice_matrix_ij=link_slice_matrix_array[3*(alpha*i+j):3*(alpha*i+j+1)].tolist()
        reconstruct_slice=[rrokvs.decode([first_slice[i]],link_vec,minibin_capacity)[0] for link_vec in link_slice_matrix_ij]
        reconstruct_slices[i][j]=reconstruct_slice
        
data_to_client=(srv_answer,reconstruct_slices)
response_to_be_sent = zlib.compress(pickle.dumps(data_to_client, protocol=pickle.HIGHEST_PROTOCOL))
t5 = time()
print('*Calculate all homomorphic operations,time{:.2f}s'.format(t5 - t4))  
s2c_response_commu = len(response_to_be_sent)
(ciphertexts,reconstruct_slices) = pickle.loads(zlib.decompress(response_to_be_sent))

decryptions = []
for ct in ciphertexts:
    decryptions.append(ts.bfv_vector_from(private_context, ct).decrypt())

# link_slice_matrix_array=link_slice_matrix.toarray()
with open(clientset_file, 'r') as g:
    client_set_entries = g.readlines()
client_intersection = []
VBF_PRFed_common_element_set=set()
for j in range(alpha):
    for i in range(table_size):
        if decryptions[j][i] == 0:
            remain_slice=dict_index_itemslice[i][1:]
            if(remain_slice==reconstruct_slices[i][j]):#第2，3，...分片全部相等
                # The index i is the location of the element in the intersection
                # Here we recover this element from the Cuckoo hash structure
                VBF_PRFed_common_element = reconstruct_item(CH.data_structure[i], i, cuckoo_hash_seeds[CH.data_structure[i] % 4])
                VBF_PRFed_common_element_set.add(VBF_PRFed_common_element)
for key,value in VBF_PRF_link.items():
    if all(num in VBF_PRFed_common_element_set for num in value):  
        # 如果value中的两个整数都在VBF_PRFed_common_element_set中，则将key添加到结果列表中  
        index = PRFed_client_set.index(key)
        client_intersection.append(client_set_entries[int(index/label_size)][:-1])
t6=time()
print("*Decrypt data to obtain intersection results,time:{:.2f}s".format(t6 - t5))
h = open(intersection_file, 'r')
real_intersection = [line[:-1] for line in h]
h.close()
print('*Intersection recovered correctly: {}'.format(set(real_intersection)==set(client_intersection)))
print('*Client ONLINE computation time {:.2f}s'.format(t6 - t0 ))
print('*Communication size:')
print('    ~ Client --> Server:  {:.2f} MB'.format((c2s_oprf_commu + c2s_query_commu )/ (2 ** 20)))
print('    ~ Server --> Client:  {:.2f} MB'.format((s2c_oprf_commu + s2c_response_commu )/ (2 ** 20)))
