import socket
import tenseal as ts
import pickle,zlib,rrokvs
import numpy as np
from math import log2

from parameters import bin_capacity, alpha, ell,output_bits
from auxiliary_functions import power_reconstruct
from oprf import server_prf_online_parallel

oprf_server_key = 1234567891011121314151617181920
from time import time

base = 2 ** ell
table_size=2**output_bits
minibin_capacity = int(bin_capacity / alpha)
logB_ell = int(log2(minibin_capacity) / ell) + 1 # <= 2 ** HE.depth
# 创建一个新的socket对象，指定IPv4地址族（AF_INET）和TCP传输协议（SOCK_STREAM)
serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serv.bind(('localhost', 4470)) #绑定socket到特定的地址和端口 
serv.listen(1)# 开始监听连接请求，参数1表示最大连接数（这里为1，即一次只能处理一个连接）

with open('server_preprocessed.pkl', 'rb') as g:
    (poly_coeffs,link_slice_matrix) = pickle.load(g)

# For the online phase of the server, we need to use the columns of the preprocessed database
transposed_poly_coeffs = np.transpose(poly_coeffs).tolist() #数组转置

for i in range(1):
    conn, addr = serv.accept()#接受客户端的连接请求，并返回一个新的套接字对象 conn 和客户端地址 addr。
    L = conn.recv(10).decode().strip()#从连接 conn 接收10 字节的数据,进而获取到接下来发送的数据流的长度。
    L = int(L, 10)
    # OPRF layer: the server receives the encoded set elements as curve points
    encoded_client_set_serialized = b""
    while len(encoded_client_set_serialized) < L:
        data = conn.recv(8192)
        if not data: break
        encoded_client_set_serialized += data   
    encoded_client_set = pickle.loads(zlib.decompress(encoded_client_set_serialized))
    t0 = time()
    # The server computes (parallel computation) the online part of the OPRF protocol, using its own secret key
    PRFed_encoded_client_set = server_prf_online_parallel(oprf_server_key, encoded_client_set)
    PRFed_encoded_client_set_serialized = zlib.compress(pickle.dumps(PRFed_encoded_client_set, protocol=pickle.HIGHEST_PROTOCOL))
    L = len(PRFed_encoded_client_set_serialized)
    sL = str(L) + ' ' * (10 - len(str(L))) #pad len to 10 bytes

    conn.sendall((sL).encode())
    conn.sendall(PRFed_encoded_client_set_serialized)
    t1 = time()
    print('*OPRF phase time:{:.2f}s'.format(t1 - t0))
    L = conn.recv(10).decode().strip()
    L = int(L, 10)

    # The server receives bytes that represent the public HE context and the query ciphertext
    final_data = b""
    while len(final_data) < L:
        data = conn.recv(8192)
        if not data: break
        final_data += data

    t2 = time()  
    print('*Received encrypted ciphertext for the first slice from the client,time:{:.2f}s'.format(t2 - t1))  
    # Here we recover the context and ciphertext received from the received bytes
    (enc_message_to_be_sent,first_slice) = pickle.loads(zlib.decompress(final_data))
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
            reconstruct_slice=[]
            for link_vec in link_slice_matrix_ij:
                reconstruct_slice.append(rrokvs.decode([first_slice[i]],link_vec,minibin_capacity)[0])
            reconstruct_slices[i][j]=reconstruct_slice
           
    data_to_client=(srv_answer,reconstruct_slices)
    response_to_be_sent = zlib.compress(pickle.dumps(data_to_client, protocol=pickle.HIGHEST_PROTOCOL))
    t3 = time()
    print('*Calculate all homomorphic operations,time{:.2f}s'.format(t3 - t2))  
    L = len(response_to_be_sent)
    sL = str(L) + ' ' * (10 - len(str(L))) #pad len to 10 bytes

    conn.sendall((sL).encode())
    conn.sendall(response_to_be_sent)
    t4 = time()
    print('*sending the ciphertext polynomial,time{:.2f}s'.format(t4 - t3))  
    # Close the connection
    print("Client disconnected \n")
    print('Server ONLINE computation time {:.2f}s'.format(t1 - t0 + t3 - t2))

    conn.close()
    serv.close()
