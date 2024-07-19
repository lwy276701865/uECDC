from math import log2

# sizes of databases of server and client
# size of intersection should be less than size of client's database
server_size = 2 ** 14
client_size = 1000
intersection_size = 700

# seeds used by both the Server and the Client for the Murmur hash functions
VBF_hash_seeds = [1111111111,2222222222]
cuckoo_hash_seeds = [123456789, 10111213141516, 17181920212223]
split_hash_seeds = [11111,22222,33333,44444]
# output_bits = number of bits of output of the hash functions
# number of bins for simple/Cuckoo Hashing = 2 ** output_bits
output_bits = 14

# encryption parameters of the BFV scheme: the plain modulus and the polynomial modulus degree
plain_modulus = 536903681
poly_modulus_degree = 2 ** 14

# the number of hashes we use for simple/Cuckoo hashing
number_of_hashes = 3

# length of the database items
sigma_max = int(log2(plain_modulus)) + output_bits - (int(log2(number_of_hashes)) + 1) 

# B = [68, 176, 536, 1832, 6727] for log(server_size) = [16, 18, 20, 22, 24]
bin_capacity = 536

# partitioning parameter
alpha = 16

# windowing parameter
ell = 2

#分片数slice number
slice_number=4

dummy_msg_server = 2 ** 512
dummy_msg_client = 2 ** 513-1
#RB-OKVS相关参数
epsilon=0.1 #错误率
omega=24#随机带状矩阵中01字符串的长度，论文中指出最佳曲线满足lambda=0.2691*omega-15.21。此时lambda=40,omega=205
construct_matrix_hashseeds=[705743854180,630853469229]