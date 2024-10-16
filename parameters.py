from math import log2

# sizes of databases of server and client
# size of intersection should be less than size of client's database
server_size = 2**14
client_size = 256
intersection_size = 200

# seeds used by both the Server and the Client for the Murmur hash functions
VBF_hash_seeds = [1111111111,2222222222]
cuckoo_hash_seeds = [123456789, 10111213141516, 17181920212223]
split_hash_seeds = [11111,22222,33333,44444]
# output_bits = number of bits of output of the hash
# number of bins for simple/Cuckoo Hashing = 2 ** output_bits
# 14 when client_size=1024;13 when client_size=512;12 when client_size=256
output_bits = 12

# encryption parameters of the BFV scheme: the plain modulus and the polynomial modulus degree
plain_modulus = 65537
poly_modulus_degree = 2 ** output_bits

# the number of hashes we use for simple/Cuckoo hashing
number_of_hashes = 3
# length of the database items
sigma_max = int(log2(plain_modulus)) + output_bits - (int(log2(number_of_hashes)) + 1)
""" Reference only.
client_size=256
B = [160,575 , 2060] for log(server_size) = [14,16, 18] when label size=5
B = [140, 460, 1680] for log(server_size) = [14,16, 18] when label size=4
B = [110,350, 1290] for log(server_size) = [14,16, 18] when label size=3
B = [55,150, 480] for log(server_size) = [14,16, 18] when label size=1

client_size=512
B = [100, 310, 1100] for log(server_size) = [14,16, 18] when label size=5
B = [80, 250, 900] for log(server_size) = [14,16, 18] when label size=4
B = [65, 200, 700,] for log(server_size) = [14,16, 18] when label size=3
B = [30,80,250] for log(server_size) = [14,16, 18] when label size=1

client_size=1024
B = [60, 240, 650] for log(server_size) = [14,16, 18] when label size=5
B = [50, 150, 600] for log(server_size) = [14,16, 18] when label size=4
B = [40, 120 400] for log(server_size) = [14,16, 18] when label size=3
B = [30, 50 150] for log(server_size) = [14,16, 18] when label size=1
"""
bin_capacity = 55
# partitioning parameter
alpha = 16
# windowing parameter
ell = 2
#slice number
slice_number=4
dummy_msg_server = 2 ** 512
dummy_msg_client = 2 ** 513-1

item_size=32
label_size=1

#You can set this parameter according to your hardware configuration. This Reference setting is determined by my environment.
if(server_size == 2**18 and label_size==5):
    cal_pax_process_num=4
elif(server_size == 2**18 and label_size==4):
    cal_pax_process_num=5
elif(server_size == 2**18 and label_size==3):
    cal_pax_process_num=6
else:
    cal_pax_process_num=8
"""
In fact, due to the generation of a large number of random numbers, the parameter settings in this document are for reference only.
Especially, bugs similar to the one below may occur during use:
(1)Paxos error, Duplicate keys were detected at idx  A, key=1cbf501973860cc7b0777d617f6f6b25...(The probability of this bug is extremely low).
(2)Simple hashing aborted...(The probability of this bug will be slightly higher).
Here are the corresponding solutions:
(1)please run set_gen.py again until no errors are reported.
(2)Increase the value of parameter 'bin_capacity' until no errors are reported.
"""