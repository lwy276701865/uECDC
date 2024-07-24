from math import log2
import numpy as np,hashlib,mmh3,rrokvs
from parameters import ell, plain_modulus, bin_capacity, alpha,dummy_msg_client,dummy_msg_server,split_hash_seeds,slice_number
base = 2 ** ell#windowing parameter
minibin_capacity = int(bin_capacity / alpha)# minibin_capacity = B / alpha
logB_ell = int(log2(minibin_capacity) / ell) + 1 # <= 2 ** HE.depth = 16  
t = plain_modulus

def int2base(n, b):
    '''
    :param n: an integer
    :param b: a base
    :return: an array of coefficients from the base decomposition of an integer n with coeff[i] being the coeff of b ** i
    '''
    if n < b:
        return [n]
    else:
        return [n % b] + int2base(n // b, b)  

# We need len(powers_vec) <= 2 ** HE.depth
def low_depth_multiplication(vector):
    '''
    :param: vector: a vector of integers 
    :return: an integer representing the multiplication of all the integers from vector
    '''
    L = len(vector)
    if L == 1:
        return vector[0]
    if L == 2:
        return(vector[0] * vector[1])
    else:    
        if (L % 2 == 1):
            vec = []
            for i in range(int(L / 2)):
                vec.append(vector[2 * i] * vector[2 * i + 1])
            vec.append(vector[L-1])
            return low_depth_multiplication(vec)
        else:
            vec = []
            for i in range(int(L / 2)):
                vec.append(vector[2 * i] * vector[2 * i + 1])
            return low_depth_multiplication(vec)

def power_reconstruct(window, exponent):
    '''
    :param: window: a matrix of integers as powers of y; in the protocol is the matrix with entries window[i][j] = [y ** i * base ** j]
    :param: exponent: an integer, will be an exponent <= logB_ell
    :return: y ** exponent
    '''
    e_base_coef = int2base(exponent, base)
    necessary_powers = [] #len(necessary_powers) <= 2 ** HE.depth 
    j = 0
    for x in e_base_coef:
        if x >= 1:
            necessary_powers.append(window[x - 1][j])
        j = j + 1
    return low_depth_multiplication(necessary_powers)


def windowing(y, bound, modulus):
    '''
    :param: y: an integer
    :param bound: an integer
    :param modulus: a modulus integer
    :return: a matrix associated to y, where we put y ** (i+1)*base ** j mod modulus in the (i,j) entry, as long as the exponent of y is smaller than some bound
    '''
    windowed_y = [[None for j in range(logB_ell)] for i in range(base-1)]
    for j in range(logB_ell):
        for i in range(base-1):
            if ((i+1) * base ** j - 1 < bound):
                windowed_y[i][j] = pow(y, (i+1) * base ** j, modulus)
    return windowed_y


def coeffs_from_roots(roots, modulus):
    '''
    :param roots: an array of integers-------
    :param modulus: an integer
    :return: coefficients of a polynomial whose roots are roots modulo modulus
    '''
    coefficients = np.array(1, dtype=np.int64)
    for r in roots:
        coefficients = np.convolve(coefficients, [1, -r]) % modulus
    return coefficients
def split_integers_unique_first_block(arr, slice_num):
    result = []
    dummy_num=0
    for idx, num in enumerate(arr):
        splits = []
        # Hash the number with index to ensure uniqueness
        if(num==dummy_msg_client or num==dummy_msg_server):
            hash_input = str(num)+str(dummy_num)+ 'some_random_string'
            dummy_num=dummy_num+1
            hash_value = int(hashlib.sha256(hash_input.encode('utf-8')).hexdigest(), 16)
            for i in range(slice_num):
                split_value = (hash_value >> (i * 16)) &0xFFFF # Extract 16-bit blocks
                splits.append(split_value)
        else:
            for split_hash_seed in split_hash_seeds:
                hash_value=mmh3.hash(str(num), signed=False,seed=split_hash_seed)
                splits.append(hash_value)

        result.append(splits)
    
    return result
def cal_polycoeef_pax(bin_list,SH):
    poly_coeffs = []
    link_slice_matrix=[]
    for i in bin_list:
    # we create a list of coefficients of all minibins from concatenating the list of coefficients of each minibin
        coeffs_from_bin = []
        for j in range(alpha):
            allslice_minibin=[]#All slices of all elements in the sub bin
            OKVS_encoding_list=[]#A slice link matrix for a sub bin
            minibin_items = [SH.simple_hashed_data[i][minibin_capacity * j + r] for r in range(minibin_capacity)]
            allslice_minibin=split_integers_unique_first_block(minibin_items,slice_number)
            slice_matrix=np.column_stack(allslice_minibin)
            first_slices=slice_matrix[0].tolist()
            for slice_id in range(1,slice_number):#Traverse the 2nd, 3rd, Sliced number slice
                link_vec=rrokvs.encode(first_slices,slice_matrix[slice_id].tolist(),len(first_slices))
                OKVS_encoding_list.append(link_vec)#Link the first slice and slice_id slice of all elements together
            coeffs_from_bin = coeffs_from_bin +coeffs_from_roots(first_slices, plain_modulus).tolist()#calculate the noemal polynomial of the first slice
            link_slice_matrix+=OKVS_encoding_list
        poly_coeffs.append(coeffs_from_bin)
    return poly_coeffs,link_slice_matrix