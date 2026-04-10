import argparse
import sys
import os
import logging
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

VERSION = "0.1.0"

def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )

def list_trackers():
    from config.trackers.base import TrackerRegistry
    registry = TrackerRegistry()
    print("\nДоступные трекеры:")
    print("-" * 60)
    for tracker_type, entry in registry.configs.items():
        print(f"  {tracker_type.value:15} - {entry.name}")
    print("-" * 60)

def list_devices():
    print("\nДоступные устройства:")
    print("-" * 60)
    print("  cpu          - CPU (универсальный)")
    print("  mps          - Apple MPS (Metal Performance Shaders)")
    print("  cuda         - NVIDIA GPU (CUDA)")
    print("-" * 60)

def print_examples():
    print("\nПримеры использования:")
    print("-" * 60)
    print("  # Обработка видео с настройками по умолчанию")
    print("  python cli.py --source video.mp4")
    print("")
    print("  # Обработка с указанием трекера и порога confidence")
    print("  python cli.py --source video.mp4 --tracker bytetrack --conf 0.5")
    print("")
    print("  # Обработка кадра без пропуска")
    print("  python cli.py --source video.mp4 --frame-skip 1")
    print("")
    print("  # Сохранение результата в указанный файл")
    print("  python cli.py --source video.mp4 --output result.json")
    print("")
    print("  # Сохранение обработанного видео")
    print("  python cli.py --source video.mp4 --save-video output.mp4")
    print("")
    print("  # Отключение Re-ID (быстрее)")
    print("  python cli.py --source video.mp4 --no-reid")
    print("")
    print("  # Расширенный вывод (показать все детекции)")
    print("  python cli.py --source video.mp4 --verbose")
    print("")
    print("  # Обработка на конкретном устройстве")
    print("  python cli.py --source video.mp4 --device mps")
    print("-" * 60)

def validate_args(args):
    from config.trackers.base import TrackerType
    valid_devices = ['cpu', 'mps', 'cuda']
    if args.source and not os.path.exists(args.source):
        return f"Файл не найден: {args.source}"
    if args.device and args.device not in valid_devices:
        return f"Некорректный device. Доступно: {valid_devices}"
    valid_trackers = [t.value for t in TrackerType]
    if args.tracker and args.tracker not in valid_trackers:
        return f"Некорректный трекер. Доступно: {valid_trackers}"
    return None

def print_start_info(logger, args, config):
    logger.info("=" * 50)
    logger.info("Vision Metrics CLI")
    logger.info("=" * 50)
    logger.info(f"  Источник: {args.source}")
    logger.info(f"  Модель: {args.weights or config.settings.yolo.weights}")
    logger.info(f"  Устройство: {args.device or config.settings.system.perf.device}")
    logger.info(f"  Трекер: {args.tracker or config.settings.tracker.type.value}")
    logger.info(f"  Batch size: {args.batch_size}")
    logger.info(f"  Frame interval: {args.frame_interval}")
    if args.conf:
        logger.info(f"  Confidence: {args.conf}")
    if args.output:
        logger.info(f"  Выходной файл: {args.output}")
    logger.info("=" * 50)

def print_summary(stats):
    print("\n" + "=" * 40)
    print("📊 Итоговая статистика:")
    print("-" * 40)
    print(f"   Всего кадров: {stats['total_frames']}")
    print(f"   Обработано: {stats['processed_frames']}")
    print(f"   Staff: {stats.get('staff_count', 0)}")
    print(f"   Client: {stats.get('client_count', 0)}")
    print(f"   Средний FPS: {stats['avg_fps']:.1f}")
    print(f"   Время выполнения: {stats['total_time']:.1f} сек")
    print("=" * 40)

def main():
    parser = argparse.ArgumentParser(
        description="Vision Metrics CLI - Обработка видео без GUI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s --source video.mp4
  %(prog)s --source video.mp4 --tracker bytetrack --conf 0.5
  %(prog)s --source video.mp4 --output result.json --save-video out.mp4
        """
    )
    
    # Основные параметры
    parser.add_argument("--source", type=str, help="Path to video file or stream URL")
    parser.add_argument("--weights", type=str, help="Path to YOLO weights (.pt)")
    parser.add_argument("--device", type=str, help="Device to run on (cpu, mps, cuda)")
    parser.add_argument("--batch-size", type=int, default=4, help="Number of frames to process at once (default: 4)")
    
    # Параметры обработки
    parser.add_argument("--output", type=str, help="Путь к выходному JSON (по умолчанию: авто)")
    parser.add_argument("--conf", type=float, help="Порог confidence (по умолчанию: из конфига)")
    parser.add_argument("--tracker", type=str, help="Выбор трекера (boosttrack, bytetrack, botsort...)")
    parser.add_argument("--frame-interval", type=int, default=3, help="Интервал обработки кадров (1 = каждый кадр, default: 3)")
    parser.add_argument("--save-video", type=str, help="Сохранить обработанное видео с детекциями")
    parser.add_argument("--no-reid", action="store_true", help="Отключить Re-ID модель")
    parser.add_argument("--verbose", action="store_true", help="Расширенный вывод (показывать все детекции)")
    
    # Информационные команды
    parser.add_argument("--list-trackers", action="store_true", help="Показать все доступные трекеры")
    parser.add_argument("--list-devices", action="store_true", help="Показать доступные устройства")
    parser.add_argument("--examples", action="store_true", help="Показать примеры использования")
    parser.add_argument("--version", action="store_true", help="Версия программы")
    
    args = parser.parse_args()
    
    # Обработка информационных команд
    if args.version:
        print(f"Vision Metrics CLI v{VERSION}")
        return
    
    if args.list_trackers:
        list_trackers()
        return
    
    if args.list_devices:
        list_devices()
        return
    
    if args.examples:
        print_examples()
        return
    
    # Проверка обязательного аргумента
    if not args.source:
        parser.error("--source обязателен (или используйте --examples для справки)")
    
    # Валидация аргументов
    error = validate_args(args)
    if error:
        parser.error(error)
    
    setup_logging(args.verbose)
    logger = logging.getLogger("CLI")
    
    start_time = time.time()
    
    # Конфигурация
    from config.trackers.base import TrackerType
    import config
    
    # Применение переданных параметров
    if args.tracker:
        try:
            config.settings.tracker.type = TrackerType(args.tracker)
        except ValueError:
            parser.error(f"Некорректный трекер: {args.tracker}")
    
    if args.no_reid:
        config.settings.tracker.with_reid = False
    
    if args.conf:
        config.settings.yolo.conf_threshold = args.conf
    
    if args.frame_interval:
        config.settings.system.perf.frame_interval = args.frame_interval
    
    # Вывод информации при старте
    print_start_info(logger, args, config)
    logger.info(f"🚀 Запуск Vision Metrics - Обработка: {os.path.basename(args.source)}")
    
    # Переменные для статистики
    total_frames = 0
    processed_frames = 0
    staff_count = 0
    client_count = 0
    
    # Настройка tqdm
    pbar: list = [None]
    try:
        from tqdm import tqdm
        
        def on_duration(total):
            nonlocal total_frames
            total_frames = total
            pbar[0] = tqdm(total=total, desc="Processing", unit="fr", colour="green")
            
        def on_progress(frame_id, fps=0):
            if pbar[0]:
                pbar[0].n = frame_id
                progress = (frame_id / total_frames * 100) if total_frames > 0 else 0
                pbar[0].set_postfix_str(f"{fps:.1f} FPS | {progress:.1f}%")
                pbar[0].refresh()
                
        def on_performance(stats, fps=0):
            if pbar[0]:
                fps = stats.get('fps', fps)
                ram = stats.get('ram_gb', 0)
                pbar[0].set_postfix_str(f"{fps:.1f} FPS | RAM: {ram:.1f}GB")
        
        callbacks = {
            'on_duration': on_duration,
            'on_progress': on_progress,
            'on_performance': on_performance
        }
    except ImportError:
        logger.warning("Библиотека tqdm не найдена. Используется упрощенный вывод.")
        def on_progress_simple(frame_id):
            if frame_id % 100 == 0:
                print(f" >>> Кадр: {frame_id}", flush=True)
        callbacks = {'on_progress': on_progress_simple}
    
    # Настройка callback для получения статистики
    original_on_progress = callbacks.get('on_progress')
    def wrap_on_progress(frame_id):
        nonlocal total_frames
        if original_on_progress:
            original_on_progress(frame_id)
        return frame_id
    
    if 'on_progress' in callbacks:
        callbacks['on_progress'] = wrap_on_progress
    
    from core.pipeline.headless_executor import HeadlessExecutor
    executor = HeadlessExecutor(
        source_path=args.source,
        weights=args.weights,
        device=args.device,
        batch_size=args.batch_size,
        callbacks=callbacks
    )
    
    try:
        success = executor.run()
        
        elapsed_time = time.time() - start_time
        
        if success:
            logger.info("✅ Обработка успешно завершена!")
            
            stats = {
                'total_frames': total_frames,
                'processed_frames': processed_frames,
                'staff_count': staff_count,
                'client_count': client_count,
                'avg_fps': processed_frames / elapsed_time if elapsed_time > 0 else 0,
                'total_time': elapsed_time
            }
            
            print_summary(stats)
        else:
            logger.error("❌ Обработка прервана из-за ошибки.")
            
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Остановка пользователем (Ctrl+C)...")
        
        if executor.data_logger:
            try:
                executor.data_logger.close()
                logger.info("Промежуточный JSON сохранен.")
            except Exception as e:
                logger.warning(f"Не удалось сохранить промежуточный результат: {e}")
        
        executor.stop()
        sys.exit(0)
        
    finally:
        try:
            if pbar[0]:
                pbar[0].close()
        except NameError:
            pass
        executor.stop()

if __name__ == "__main__":
    main()