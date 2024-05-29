from random import choices,choice
from parameters import server_size, client_size, intersection_size

server_list = []
while len(server_list) < server_size:
    # 生成一个64位的随机二进制字符串  
    item_string = '1'+''.join(choices(['0', '1'], k=63))  
    # 将二进制字符串转换为十进制整数  
    item = int(item_string, 2)
    label_string = '1'+''.join(choices(['0', '1'], k=31))   
    label = int(label_string, 2)    
    # item = randint(0, 2 ** 63 - 1)
    # label = randint(0, 2 ** 32 - 1)
    server_list.append((item, label))
print('Done creating server\'s set')

client_set = set()
while len(client_set) < min(intersection_size, client_size):
    item = choice(server_list)
    label=item[1]^2 #将标签数据倒数第二位翻转，即错误分类标签
    client_set.add((item[0], label))

while len(client_set) < client_size:
    item_string = '1'+''.join(choices(['0', '1'], k=63)) 
    item = int(item_string, 2)
    label_string = '1'+''.join(choices(['0', '1'], k=31))   
    label = int(label_string, 2)
    client_set.add((item, label))
print('Done creating client\'s set')
#set elements can be integers < order of the generator of the elliptic curve (192 bits integers if P192 is used); 'sample' works only for a maximum of 63 bits integers.
# disjoint_union=[(randint(0, 2 ** 63 - 1), randint(0, 2 ** 32 - 1)) for _ in range(server_size+client_size)]
# intersection = disjoint_union[:intersection_size]
# server_set = intersection + disjoint_union[intersection_size: server_size]
# client_set = intersection + disjoint_union[server_size: server_size - intersection_size + client_size]
	
with open("server_set.csv", "w") as server_file:
    for index,(item, label) in enumerate(server_list):
        server_file.write(str(item) + "," + str(label))
        if index < len(server_list) - 1:  
            server_file.write('\n')
print('Wrote server\'s set')

with open("client_set.csv", "w") as client_file:
    for index,(item, label) in enumerate(client_set):
        client_file.write(str(item) + "," + str(label))
        if index < len(client_set) - 1:  
            client_file.write('\n')
print('Wrote receiver\'s set')
