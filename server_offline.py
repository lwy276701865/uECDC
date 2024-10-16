from parameters import number_of_hashes, bin_capacity, alpha,VBF_hash_seeds,cuckoo_hash_seeds,output_bits,dummy_msg_server,cal_pax_process_num
from simple_hash import Simple_hash
from auxiliary_functions import cal_polycoeef_pax
from oprf import server_prf_offline_parallel, order_of_generator, G
from time import time
from multiprocessing import Pool
from functools import partial
import numpy as np
import pickle,mmh3
from scipy.sparse import csr_matrix
#server's PRF secret key
oprf_server_key = 1234567891011121314151617181920
table_size=2**output_bits
# key * generator of elliptic curve
server_point_precomputed = (oprf_server_key % order_of_generator) * G
t0 = time()
server_set = []
with open('server_set.csv', 'r') as f:
    lines = f.readlines()
    for line in lines:
        item,label=line[:-1].split(",")
        binary_item = bin(int(item))[2:]
        binary_label = bin(int(label))[2:]
        for i in range(len(binary_label)):
            # Splicing the binary string of binary_item and the current bit of binary_1abel  
            binary_item = binary_item + binary_label[i]  
            decimal_value = int(binary_item, 2)  
            server_set.append(decimal_value)  

#The PRF function is applied on the set of the server, using parallel computation
PRFed_server_set = server_prf_offline_parallel(server_set, server_point_precomputed)
PRFed_server_set = set(PRFed_server_set)
t1 = time()
print("*OPRF phase time:{:.2f}s".format(t1 - t0))

minibin_capacity = int(bin_capacity / alpha)
VBF_PRFed_server_set=set()
for item in PRFed_server_set:
    for i in range(2):
        VBF_PRFed_server_set.add(mmh3.hash128(str(item), VBF_hash_seeds[i], signed=False))
# The OPRF-processed database entries are simple hashed
SH = Simple_hash(cuckoo_hash_seeds)
for item in VBF_PRFed_server_set:
    for i in range(number_of_hashes): #range(3)=[0,1,2]
        SH.insert(item, i)
# simple_hashed_data is padded with dummy_msg_server
for i in range(table_size):
    for j in range(bin_capacity):
        if SH.simple_hashed_data[i][j] == None:
            SH.simple_hashed_data[i][j] = dummy_msg_server

# Here we perform the partitioning:
# Namely, we partition each bin into alpha minibins with B/alpha items each
# We represent each minibin as the coefficients of a polynomial of degree B/alpha that vanishes in all the entries of the mininbin
# Therefore, each minibin will be represented by B/alpha + 1 coefficients; notice that the leading coeff = 1
# After partitioning, we will split each element in each sub bin into multiple small data slice and link them together
t2 = time()
print("*Simple hashing phase time:{:.2f}s".format(t2 - t1))
poly_coeffs = []
link_slice_matrix=[]
arr = np.arange(table_size)  
bin_array = np.array_split(arr, cal_pax_process_num)
bin_lists = [list(bin) for bin in bin_array]
outputs=[]
partial_func = partial(cal_polycoeef_pax, SH=SH)  
with Pool(cal_pax_process_num) as p:
    outputs = p.map(partial_func, bin_lists)
for output in outputs:
    poly_coeffs+=output[0]
    link_slice_matrix+=output[1]
link_slice_matrix_array=np.array(link_slice_matrix,dtype=np.uint32)
t3 = time()
data_to_save = (poly_coeffs,csr_matrix(link_slice_matrix_array))
with open('server_preprocessed.pkl', 'wb') as f:
    pickle.dump(data_to_save, f)
t4 = time()
print('*construct normal polynomial and rrokvs phase time: {:.2f}s'.format(t3 - t2))
print('*write file time:{:.2f}s'.format(t4 - t3))
print('*Server OFFLINE time {:.2f}s'.format(t4 - t0))
