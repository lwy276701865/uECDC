import pickle
from oprf import client_prf_offline, order_of_generator, G
from time import time

# client's PRF secret key (a value from  range(order_of_generator))
oprf_client_key = 12345678910111213141516171819222222222222
t0 = time()

# key * generator of elliptic curve
client_point_precomputed = (oprf_client_key % order_of_generator) * G

client_set = []
with open('client_set.csv', 'r') as f:
    lines = f.readlines()
    for line in lines:
        item,label=line[:-1].split(",")
        binary_item = bin(int(item))[2:]
        binary_label = bin(int(label))[2:]
        for i in range(len(binary_label)):
            # 拼接binary_item的二进制字符串和binary_label的当前位  
            concat_binary_item = binary_item + str(int(binary_label[:i+1])^1)  
            # 将拼接后的二进制字符串转换回十进制  
            decimal_value = int(concat_binary_item, 2)  
            # 将十进制值添加到结果数组中  
            client_set.append(decimal_value) 
# OPRF layer: encode the client's set as elliptic curve points.
encoded_client_set = [client_prf_offline(item, client_point_precomputed) for item in client_set]

with open('client_preprocessed.pkl', 'wb') as g:
    pickle.dump(encoded_client_set, g)	 
t1 = time()
print('Client OFFLINE time: {:.2f}s'.format(t1-t0))
