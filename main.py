from parser import get_robots_rules
from crawler import crawl
def main():
    crawl("https://www.bt.dk", max_pages=1000)
    print("Done.")

if __name__ == "__main__":
    main()