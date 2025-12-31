"""
并行处理工具
支持批量导出，避免内存溢出
符合 fuction.txt 要求：批量导出并行处理，避免内存溢出，大文件分块处理
"""
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from typing import List, Callable, Any, Dict
from pathlib import Path
import multiprocessing
import gc
import os


class ParallelProcessor:
    """
    并行处理器
    用于批量导出多份文档，支持并行处理和内存管理
    """
    
    def __init__(
        self,
        max_workers: int = None,
        use_threads: bool = None,
        chunk_size: int = 1024
    ):
        """
        初始化并行处理器
        符合 fuction.txt 要求：批量导出并行处理，避免内存溢出
        
        Args:
            max_workers: 最大工作线程/进程数（默认使用 CPU 核心数）
            use_threads: 是否使用线程池（None 自动选择，Windows 默认使用线程池）
            chunk_size: 大文件分块大小（KB），用于内存管理
        """
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.chunk_size = chunk_size * 1024  # 转换为字节
        
        # Windows 上默认使用线程池（避免进程池问题）
        # 其他系统可以使用进程池（性能更好）
        if use_threads is None:
            import platform
            # Windows 上使用线程池，避免进程池的导入问题
            use_threads = platform.system() == 'Windows'
        
        self.use_threads = use_threads
        
        # 选择执行器类型
        if use_threads:
            self.executor_class = ThreadPoolExecutor
        else:
            self.executor_class = ProcessPoolExecutor
    
    def process_batch(
        self,
        tasks: List[Dict[str, Any]],
        process_func: Callable[[Dict[str, Any]], Any],
        callback: Callable[[Any], None] = None
    ) -> List[Any]:
        """
        批量处理任务（并行执行）
        
        Args:
            tasks: 任务列表，每个任务是一个字典
            process_func: 处理函数，接收任务字典，返回处理结果
            callback: 回调函数（可选），每个任务完成时调用
        
        Returns:
            处理结果列表
        """
        results = []
        errors = []
        
        # 使用执行器并行处理
        with self.executor_class(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(process_func, task): task
                for task in tasks
            }
            
        # 收集结果（性能优化：内存管理）
        completed_count = 0
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                results.append(result)
                completed_count += 1
                
                # 调用回调函数
                if callback:
                    callback(result)
                
                # 每完成10个任务，执行一次垃圾回收（避免内存溢出）
                if completed_count % 10 == 0:
                    gc.collect()
                    
            except Exception as e:
                error_info = {
                    'task': task,
                    'error': str(e),
                    'type': type(e).__name__
                }
                errors.append(error_info)
                print(f"任务失败: {task}, 错误: {e}")
        
        # 最终垃圾回收
        gc.collect()
        
        # 如果有错误，记录但继续执行
        if errors:
            print(f"完成处理，成功: {len(results)}, 失败: {len(errors)}")
        
        return results
    
    def process_large_file(
        self,
        file_path: Path,
        process_chunk: Callable[[bytes], Any]
    ) -> List[Any]:
        """
        分块处理大文件，避免内存溢出
        
        Args:
            file_path: 文件路径
            process_chunk: 处理每个数据块的函数
        
        Returns:
            处理结果列表
        """
        results = []
        
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                
                try:
                    result = process_chunk(chunk)
                    results.append(result)
                except Exception as e:
                    print(f"处理数据块时出错: {e}")
                    continue
        
        return results
    
    @staticmethod
    def get_optimal_workers(task_count: int, max_workers: int = None) -> int:
        """
        计算最优工作线程/进程数
        
        Args:
            task_count: 任务数量
            max_workers: 最大工作数
        
        Returns:
            最优工作数
        """
        cpu_count = multiprocessing.cpu_count()
        max_workers = max_workers or cpu_count
        
        # 如果任务数少于 CPU 核心数，使用任务数
        # 否则使用 CPU 核心数，避免过度并行
        return min(task_count, max_workers, cpu_count)




