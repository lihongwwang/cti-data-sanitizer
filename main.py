import os
import time  # 新增导入time模块
from openai import OpenAI

# === 配置区域 ===
API_KEY = os.getenv("DEEPSEEK_API_KEY")
ROOT_SOURCE_FOLDER = "./part2"      # 主目录，包含多个子目录
ROOT_OUTPUT_FOLDER = "./cleaned_txt_part2"  # 清洗结果的主输出目录
# =================

# 初始化客户端
client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
os.makedirs(ROOT_OUTPUT_FOLDER, exist_ok=True)

SYSTEM_PROMPT = """你是一名网络安全分析师，请对文本内容进行清洗，保留与威胁分析直接相关的部分。具体移除要求如下：
移除所有非核心正文内容，包括：页眉、页脚、页码；文档元信息；免责声明、保密声明、版权说明；参考文献、以及后续阅读资料；无关的装饰符号、分隔线、水印；图表的残留信息。
保留其他所有内容。请确保输出内容整洁、连贯，适合作为语言模型输入进行进一步分析，不需要翻译。"""


def clean_single_text(raw_text):
    """调用API清洗单段文本，并返回清洗后的内容和API调用耗时"""
    try:
        api_start_time = time.time()  # API计时开始
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_text}
            ],
            stream=False,
            temperature=0.2,
        )
        api_elapsed = time.time() - api_start_time  # API计时结束
        return response.choices[0].message.content, api_elapsed
    except Exception as e:
        print(f"  调用API时出错：{e}")
        return None, 0


def process_directory(source_dir, output_dir):
    """处理单个目录中的所有txt文件"""
    # 获取当前目录下的所有txt文件（不包含子目录中的文件）
    txt_files = [f for f in os.listdir(source_dir) if
                 f.endswith('.txt') and os.path.isfile(os.path.join(source_dir, f))]

    if not txt_files:
        print(f"  目录 '{os.path.basename(source_dir)}' 中未找到 .txt 文件，跳过。")
        return 0, 0, 0, 0  # 成功数，跳过数，文件数，API总耗时

    print(f"  正在处理目录 '{os.path.basename(source_dir)}'，发现 {len(txt_files)} 个文件")

    success_count = 0
    skip_count = 0
    total_api_time = 0

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    for filename in txt_files:
        file_start_time = time.time()
        print(f"    正在处理: {filename}", end="", flush=True)

        # 读取文件
        input_path = os.path.join(source_dir, filename)
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
        except Exception as e:
            print(f" - [失败] 读取文件时出错：{e}")
            continue

        # 跳过空文件
        if not raw_content.strip():
            print(f" - [跳过] 文件为空")
            skip_count += 1
            continue

        # 调用API进行清洗
        cleaned_content, api_time = clean_single_text(raw_content)
        total_api_time += api_time

        file_elapsed = time.time() - file_start_time

        if cleaned_content is not None:
            # 保存清洗后的内容到对应的输出目录
            output_filename = f"cleaned_{filename}"
            output_path = os.path.join(output_dir, output_filename)
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                print(f" - [成功] 耗时：{file_elapsed:.2f}秒 (API: {api_time:.2f}秒)")
                success_count += 1
            except Exception as e:
                print(f" - [失败] 写入文件时出错：{e}")
        else:
            print(f" - [失败] 未能获取清洗结果")

    return success_count, skip_count, len(txt_files), total_api_time


def process_root_directory():
    """遍历主目录下的所有子目录并处理文件"""
    if not os.path.exists(ROOT_SOURCE_FOLDER):
        print(f"错误：主目录 '{ROOT_SOURCE_FOLDER}' 不存在")
        return

    print(f"开始处理主目录：{ROOT_SOURCE_FOLDER}")
    print("=" * 60)

    total_start_time = time.time()

    # 获取主目录下的所有子目录（仅一级子目录）
    all_dirs = []
    for item in os.listdir(ROOT_SOURCE_FOLDER):
        item_path = os.path.join(ROOT_SOURCE_FOLDER, item)
        if os.path.isdir(item_path):
            all_dirs.append((item, item_path))

    if not all_dirs:
        print(f"警告：主目录下未找到任何子目录")
        # 如果没有子目录，直接将主目录作为处理目标
        all_dirs = [('', ROOT_SOURCE_FOLDER)]

    print(f"发现 {len(all_dirs)} 个子目录需要处理")
    print("-" * 60)

    # 统计所有目录的汇总信息
    total_success = 0
    total_skip = 0
    total_files = 0
    total_api_time = 0
    dir_results = []

    # 遍历每个子目录进行处理
    for dir_name, source_dir in all_dirs:
        print(f"\n📁 处理目录: {dir_name if dir_name else '根目录'}")

        # 构建对应的输出目录路径，保持相同的目录结构
        if dir_name:
            output_dir = os.path.join(ROOT_OUTPUT_FOLDER, dir_name)
        else:
            output_dir = ROOT_OUTPUT_FOLDER

        # 处理当前目录
        dir_start_time = time.time()
        success, skip, file_count, api_time = process_directory(source_dir, output_dir)
        dir_elapsed = time.time() - dir_start_time

        # 记录当前目录的结果
        dir_results.append({
            'name': dir_name if dir_name else '根目录',
            'success': success,
            'skip': skip,
            'total': file_count,
            'time': dir_elapsed,
            'api_time': api_time
        })

        # 累加总数
        total_success += success
        total_skip += skip
        total_files += file_count
        total_api_time += api_time

        print(f"  ✅ 目录处理完成: 成功 {success}/{file_count}，跳过 {skip}，耗时 {dir_elapsed:.2f}秒")

    total_elapsed = time.time() - total_start_time

    # 打印详细统计报告
    print("\n" + "=" * 60)
    print("多目录处理完成！详细报告如下：")
    print("\n各目录处理情况：")
    print("-" * 40)

    for result in dir_results:
        if result['total'] > 0:
            success_rate = (result['success'] / result['total']) * 100
            print(
                f"  📁 {result['name']:20} 成功: {result['success']:3d}/{result['total']:3d} ({success_rate:5.1f}%) | 耗时: {result['time']:6.2f}秒")
        else:
            print(f"  📁 {result['name']:20} 无文件可处理")

    print("\n汇总统计：")
    print("-" * 40)
    print(f"  📂 总目录数：     {len(dir_results)} 个")
    print(f"  📄 总文件数：     {total_files} 个")
    print(f"  ✅ 成功清洗：     {total_success} 个")
    print(f"  ⏭️  跳过空文件：   {total_skip} 个")

    if total_success > 0:
        print(f"  ⚡ 平均文件处理耗时： {total_elapsed / total_success:.2f} 秒/个")
        print(f"  🖥️  API调用平均耗时： {total_api_time / total_success:.2f} 秒/次")
        if total_api_time > 0:
            api_ratio = (total_api_time / total_elapsed) * 100
            print(f"  📊 API耗时占比：     {api_ratio:.1f}%")

    print(f"  🕐 任务总耗时：    {total_elapsed:.2f} 秒")

    # 如果总耗时超过60秒，转换为分钟显示
    if total_elapsed > 60:
        minutes = int(total_elapsed // 60)
        seconds = total_elapsed % 60
        print(f"                   ({minutes}分{seconds:.2f}秒)")

    print(f"所有结果已保存至主目录：{ROOT_OUTPUT_FOLDER}")


if __name__ == "__main__":
    process_root_directory()