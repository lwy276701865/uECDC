import csv
import hashlib
from random import choice,choices
from parameters import item_size,client_size,intersection_size
def generate_hash_key(keys):
    """生成64位哈希键"""
    # 将像素值用逗号拼接成字符串
    link_str = ','.join(map(str, keys))
    # 使用SHA-256哈希并取前16位十六进制（64位）
    sha = hashlib.sha256(link_str.encode()).hexdigest()
    hex_key = sha[:16]  # 提取前16位十六进制字符（64位二进制）
    or_str="8000000000000000"
    key_num=int(hex_key, 16) | int(or_str, 16)
    return str(key_num)  # 转换为十进制整数

def process_csvdataset(input_path, output_path):
    with open(input_path, 'r') as infile, open(output_path, 'w', newline='') as outfile,\
        open("intersection_mnist.csv", 'w', newline='') as interfile,open("client_mnist.csv", 'w', newline='') as clientfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        inter_writer = csv.writer(interfile)
        client_writer = csv.writer(clientfile)
        inter_size=0
        cli_size=0
        # 跳过第一行（使用 next() 函数）
        next(reader)
        if("diabetes" in input_path):
            for row in reader:
                if not row:
                    continue  # 跳过空行  
                label=row[-2]
                keys=row[:-2]+row[-1:]     
                # 生成哈希键
                key = generate_hash_key(keys)
                # 写入键值对（键, 标签）
                writer.writerow([key, label])
                if(inter_size<intersection_size):
                    label=str(1-int(label))
                    inter_writer.writerow([key, label])
                    inter_size+=1
                    client_writer.writerow([key, label])
                    cli_size+=1
        else:#MNIST
            for row in reader:
                if not row:
                    continue  # 跳过空行
                label = row[0]
                keys = row[1:]  # 获取所有像素值
                
                # 生成哈希键
                key = generate_hash_key(keys)
                # 写入键值对（键, 标签）
                writer.writerow([key, label])
                if(inter_size<intersection_size):
                    label=str(9-int(label))
                    inter_writer.writerow([key, label])
                    inter_size+=1
                    client_writer.writerow([key, label])
                    cli_size+=1
        while cli_size < client_size:
            item_string = '1'+''.join(choices(['0', '1'], k=63))
            key = int(item_string, 2)
            if("diabetes" in input_path):
                digits = '01'
                label_string = choice(digits)
            else:
                digits = '0123456789'
                label_string = choice(digits) 
            client_writer.writerow([key, label_string])
            cli_size+=1
                
def check_hash_collision(file_path):
    keys = []
    key_set = set()
    duplicates = {}

    with open(file_path, 'r') as f:
        reader = csv.reader(f)
        for index,row in enumerate(reader):
            if not row:  # 跳过空行
                continue
            key = row[0]  # 假设键在第一列
            
            # 统计重复项
            if key in key_set:
                print(index+2)
                if key in duplicates:
                    duplicates[key] += 1
                else:
                    duplicates[key] = 2  # 第一次出现时已记录，所以初始为2
            else:
                key_set.add(key)
            keys.append(key)
    
    # 验证唯一性
    total_rows = len(keys)
    unique_count = len(key_set)
    
    print(f"总行数: {total_rows}")
    print(f"唯一键数量: {unique_count}")
    
    if unique_count == total_rows:
        print("🎉 所有键均唯一，无哈希碰撞！")
    else:
        print(f"⚠️ 发现 {total_rows - unique_count} 次哈希碰撞！")
        print("重复键及其出现次数：")
        for key, count in duplicates.items():
            print(f"  {key}: {count} 次")
    
    return duplicates
# 使用示例
# process_csvdataset("./datasets/mnist_train_test.csv", "server_mnist.csv")
check_hash_collision("server_mnist.csv")
process_csvdataset("./datasets/diabetes_dataset_with_notes.csv", "server_diabetes.csv")
check_hash_collision("server_diabetes.csv")