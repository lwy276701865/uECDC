from random import choices,choice
from parameters import server_size, client_size, intersection_size,item_size,label_size

server_list = []
ser_generated_items = set()
while len(server_list) < server_size:
    # 生成一个64位的随机二进制字符串  
    item_string = '1'+''.join(choices(['0', '1'], k=item_size-1))
    if item_string not in ser_generated_items:
        ser_generated_items.add(item_string)
        # 将二进制字符串转换为十进制整数  
        item = int(item_string, 2)
        label_string = '1'+''.join(choices(['0', '1'], k=label_size-1))   
        label = int(label_string, 2)    
        server_list.append((item, label))
print('Done creating server\'s set')

client_set = set()
while len(client_set) < min(intersection_size, client_size):
    item = choice(server_list)
    label=item[1]^2 #将标签数据倒数第二位翻转，即错误分类标签
    client_set.add((item[0], label))

h = open('intersection.csv', 'w')
for item in client_set:
	h.write(str(item[0])+','+str(item[1]) + '\n')
h.close()

while len(client_set) < client_size:
    item_string = '1'+''.join(choices(['0', '1'], k=item_size-1))
    if item_string not in ser_generated_items: 
        ser_generated_items.add(item_string)
        item = int(item_string, 2)
        label_string = '1'+''.join(choices(['0', '1'], k=label_size-1))   
        label = int(label_string, 2)
        client_set.add((item, label))
print('Done creating client\'s set')
	
with open("server_set.csv", "w") as server_file:
    for index,(item, label) in enumerate(server_list):
        server_file.write(str(item) + "," + str(label)+ '\n')
print('Wrote server\'s set')

with open("client_set.csv", "w") as client_file:
    for index,(item, label) in enumerate(client_set):
        client_file.write(str(item) + "," + str(label)+ '\n')
print('Wrote receiver\'s set')
