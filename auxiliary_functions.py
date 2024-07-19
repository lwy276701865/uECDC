from math import log2
import numpy as np,hashlib,random,string,mmh3,rrokvs
from parameters import ell, plain_modulus, bin_capacity, alpha,dummy_msg_client,dummy_msg_server,split_hash_seeds,slice_number
from hashlib import blake2b
base = 2 ** ell#窗口参数
minibin_capacity = int(bin_capacity / alpha)# minibin_capacity = B / alpha
logB_ell = int(log2(minibin_capacity) / ell) + 1 # <= 2 ** HE.depth = 16  
# logB_ell = 4 # <= 2 ** HE.depth = 16  
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
    # 计算需要在前面填充的0的数量  
    pad_width = (minibin_capacity+1 - len(coefficients), 0)  # (前面填充的数量, 后面填充的数量)  
    # 使用numpy.pad填充数组  
    padded_coefficients = np.pad(coefficients, pad_width=pad_width, mode='constant', constant_values=0)  
    return padded_coefficients
# 切分字符串，将一个字符串切为n份
def split_string_into_n_parts(arr, n):  
    slice_result = []
    for num in arr:
        s=bin(num)[2:]
        # 计算每份的长度  
        length_per_part = len(s) // n  
        # 计算剩余的长度（如果有的话）  
        remainder = len(s) % n  
        # 初始化结果列表  
        parts = []  
        # 遍历字符串，按份切分  
        start = 0  
        for i in range(n):  
            # 如果还有剩余长度，则当前份应该多取一个字符  
            end = start + length_per_part + (1 if remainder > 0 else 0)  
            # 切分字符串并添加到结果列表
            result=s[start:end].lstrip('0')
            if not result:
                result='0'
            parts.append(int(result,2))
            # 更新起始位置  
            start = end  
            # 减少剩余长度（如果有的话）  
            if remainder > 0:  
                remainder -= 1
        slice_result.append(parts)
    return slice_result
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
                hash_value=mmh3.hash(str(num)+ 'some_random_string', signed=False,seed=split_hash_seed)
                splits.append(hash_value)
            hash_input = str(num)+ 'some_random_string'
            # splits.append(num%hash_value)
        # hash_value = mmh3.hash(hash_input, signed=False)
        # hash_value =int(blake2b(hash_input.encode('utf-8')).hexdigest(),16)

        result.append(splits)
    
    return result
def cal_polycoeef_pax(bin_list,SH):
    poly_coeffs = []
    link_slice_matrix={}
    for i in bin_list:
    # we create a list of coefficients of all minibins from concatenating the list of coefficients of each minibin
        coeffs_from_bin = []
        for j in range(alpha):
            allslice_minibin=[]#一个子桶中所有元素的所有分片
            OKVS_encoding_list=[]#一个子桶的分片链接矩阵
            minibin_items = [SH.simple_hashed_data[i][minibin_capacity * j + r] for r in range(minibin_capacity)]
            # for index,item in enumerate(minibin_items):
            #     item_slice_list=split_integer_into_n_unique_parts(item,slice_number)#数据切片
            #     allslice_minibin.append(item_slice_list)
            allslice_minibin=split_integers_unique_first_block(minibin_items,slice_number)
            slice_matrix=np.column_stack(allslice_minibin)
            first_slices=slice_matrix[0].tolist()
            for slice_id in range(1,slice_number):#遍历第2分片,3,...,slice_number
                link_vec=rrokvs.encode(first_slices,slice_matrix[slice_id].tolist(),len(first_slices))
                OKVS_encoding_list.append(link_vec)#将所有元素的第一分片和第slice_id分片链接起来
            coeffs_from_bin = coeffs_from_bin +coeffs_from_roots(first_slices, plain_modulus).tolist()#只计算第一个分片的标准多项式
            link_slice_matrix[f"{i}_{j}"]=OKVS_encoding_list
        poly_coeffs.append(coeffs_from_bin)
    return poly_coeffs,link_slice_matrix