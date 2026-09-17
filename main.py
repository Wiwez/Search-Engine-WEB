from parser import get_robots_rules
def main():
    get_robots_rules("https://nytimes.com/robots.txt", "MyCrawler")
    print("Done.")

if __name__ == "__main__":
    main()