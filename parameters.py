from math import log2

# sizes of databases of server and client
# size of intersection should be less than size of client's database
server_size = 2**18
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
# client_size=256
# B = [160,550 , 2060] for log(server_size) = [14,16, 18] when label size=5
# B = [130, 460, 1680] for log(server_size) = [14,16, 18] when label size=4
# B = [110,350, 1280] for log(server_size) = [14,16, 18] when label size=3

# client_size=512
# B = [100, 310, 1100] for log(server_size) = [14,16, 18] when label size=5
# B = [80, 250, 900] for log(server_size) = [14,16, 18] when label size=4
# B = [65, 190, 700] for log(server_size) = [14,16, 18] when label size=3

# client_size=1024
# B = [60, 240, 650] for log(server_size) = [14,16, 18] when label size=5
# B = [50, 150, 600] for log(server_size) = [14,16, 18] when label size=4
# B = [40, 120 400] for log(server_size) = [14,16, 18] when label size=3
bin_capacity = 1280
# partitioning parameter
alpha = 16
# windowing parameter
ell = 2
#slice number
slice_number=4
dummy_msg_server = 2 ** 512
dummy_msg_client = 2 ** 513-1

item_size=32
label_size=3