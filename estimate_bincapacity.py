from math import log2
from math import comb

no_of_hashes = 3 
no_of_vbfhashes = 2 
m = 2 ** 12 #no of bins
server_size = 2**18
label_size=10
d = no_of_vbfhashes*no_of_hashes * server_size*label_size
security_bits = 40 #lambda

md_1 = m ** (d-1)

s = 0
S = m ** d
i = 0
power_of_m_1 = (m-1) ** d
TV = True

while TV == True:
	print(i)
	current_term = comb(d,i) * power_of_m_1
	s = s + current_term	
	S = S - current_term
	if int(log2(md_1) - log2(S)) >= security_bits:
		TV = False 
	i = i + 1
	power_of_m_1 = power_of_m_1 // (m-1)

print('--------------------')
print('bin_capacity = {}'.format(i-1))