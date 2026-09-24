from parser import get_robots_rules
from crawler import crawl
from indexing import startIndexing
def main():
    crawl("https://www.bt.dk", max_pages=200)

    startIndexing()

    print("Done.")

if __name__ == "__main__":
    main()