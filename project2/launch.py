from configparser import ConfigParser
from argparse import ArgumentParser

from utils.server_registration import get_cache_server
from utils.config import Config
from crawler import Crawler


def main(config_file, restart):
    cparser = ConfigParser()
    cparser.read(config_file)
    config = Config(cparser)
    config.cache_server = get_cache_server(config, restart)
    crawler = Crawler(config, restart)
    crawler.start()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--restart", action="store_true", default=False)
    parser.add_argument("--config_file", type=str, default="config.ini")
    args = parser.parse_args()
    main(args.config_file, args.restart)

    # ===============================
    # GENERATE REPORT AFTER CRAWLING
    # ===============================
    print("\n" + "="*80)
    print("CRAWL FINISHED - GENERATING REPORT")
    print("="*80)
    
    try:
        from scraper import save_report
        save_report()
        print("\n✅ Report successfully saved to crawler_report.txt")
        print("="*80 + "\n")
    except Exception as e:
        print(f"\n❌ Error generating report: {e}")
        print("="*80 + "\n")
