import argparse
import sys
import os
import logging

# Добавляем текущую директорию в путь поиска модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.pipeline.headless_executor import HeadlessExecutor

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )

def main():
    parser = argparse.ArgumentParser(description="Vision Metrics CLI - Headless Processing")
    parser.add_argument("--source", type=str, required=True, help="Path to video file or stream URL")
    parser.add_argument("--weights", type=str, help="Path to YOLO weights (.pt)")
    parser.add_argument("--device", type=str, help="Device to run on (cpu, mps, cuda)")
    parser.add_argument("--batch-size", type=int, default=4, help="Number of frames to process at once (e.g., 4 or 8)")
    
    args = parser.parse_args()
    setup_logging()
    
    logger = logging.getLogger("CLI")
    logger.info(f"🚀 Запуск Vision Metrics - Обработка: {os.path.basename(args.source)}")
    
    # Пытаемся использовать tqdm для красивого прогресс-бара
    try:
        from tqdm import tqdm
        pbar = [None] # Используем список для замыкания
        
        def on_duration(total):
            pbar[0] = tqdm(total=total, desc="Processing", unit="fr", colour="green")
            
        def on_progress(frame_id):
            if pbar[0]:
                pbar[0].n = frame_id
                pbar[0].refresh()
                
        def on_performance(stats):
            if pbar[0]:
                fps = stats.get('fps', 0)
                pbar[0].set_postfix(fps=f"{fps:.1f}", ram=f"{stats.get('ram_gb', 0):.1f}GB")

        callbacks = {
            'on_duration': on_duration,
            'on_progress': on_progress,
            'on_performance': on_performance
        }
    except ImportError:
        logger.warning("Библиотека tqdm не найдена. Используется упрощенный вывод.")
        def simple_progress(frame_id):
            if frame_id % 100 == 0:
                print(f" >>> Кадр: {frame_id}", flush=True)
        callbacks = {'on_progress': simple_progress}

    executor = HeadlessExecutor(
        source_path=args.source,
        weights=args.weights,
        device=args.device,
        batch_size=args.batch_size,
        callbacks=callbacks
    )
    
    try:
        success = executor.run()
        if pbar[0]:
            pbar[0].close()
            
        if success:
            logger.info("✅ Обработка успешно завершена!")
        else:
            logger.error("❌ Обработка прервана из-за ошибки.")
    except KeyboardInterrupt:
        if pbar[0]:
            pbar[0].close()
        logger.warning("\n⏹ Остановка пользователем (Ctrl+C)...")
        executor.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()
