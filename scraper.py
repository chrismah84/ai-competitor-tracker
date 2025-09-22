import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import time
import re

class AINewsTracker:
    def __init__(self, config_file='config.json'):
        self.config = self.load_config(config_file)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def load_config(self, config_file):
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config file {config_file} not found. Creating default config.")
            return {}

    def contains_ai_keywords(self, text):
        ai_keywords = self.config.get('ai_keywords', [])
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in ai_keywords)

    def scrape_tech_news(self, url, source_name):
        try:
            response = self.session.get(url, timeout=self.config.get('scraping_settings', {}).get('timeout', 10))
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            data = {
                'source': source_name,
                'url': url,
                'scraped_at': datetime.now().isoformat(),
                'title': soup.title.string if soup.title else 'No title',
                'articles': []
            }

            # Define selectors for different news sites
            selectors = {
                'TechCrunch': ['.post-block__title', '.post-block__header h2', 'h2.post-block__title'],
                'The Information': ['h3', '.headline', '.story-headline'],
                'Ars Technica': ['.listing-title', 'h2', '.story-headline'],
                'VentureBeat': ['.ArticleListing__title', 'h2', '.post-title'],
                'Wired': ['.SummaryItemHedLink-cgPazN', 'h3', '.summary-title'],
                'MIT Technology Review': ['.teaserItem__title', 'h3', '.story-title']
            }

            # Generic selectors as fallback
            generic_selectors = ['article h2', 'article h3', '.entry-title', '.article-title', 'h2 a', 'h3 a']

            site_selectors = selectors.get(source_name, generic_selectors)

            for selector in site_selectors:
                elements = soup.select(selector)
                for element in elements[:self.config.get('scraping_settings', {}).get('max_content_items', 15)]:
                    title_text = element.get_text(strip=True)

                    # Get the link if it's an anchor tag or find anchor within element
                    link = None
                    if element.name == 'a':
                        link = element.get('href')
                    else:
                        anchor = element.find('a')
                        if anchor:
                            link = anchor.get('href')

                    # Make relative URLs absolute
                    if link and link.startswith('/'):
                        from urllib.parse import urljoin
                        link = urljoin(url, link)

                    if len(title_text) > 20 and self.contains_ai_keywords(title_text):
                        article = {
                            'title': title_text[:self.config.get('scraping_settings', {}).get('max_content_length', 800)],
                            'link': link,
                            'extracted_at': datetime.now().isoformat()
                        }
                        data['articles'].append(article)

            return data

        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return None

    def scrape_website(self, url, company_name):
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            data = {
                'company': company_name,
                'url': url,
                'scraped_at': datetime.now().isoformat(),
                'title': soup.title.string if soup.title else 'No title',
                'content': []
            }

            # Extract news/blog content
            for selector in ['article', '.news-item', '.blog-post', 'h2', 'h3']:
                elements = soup.select(selector)
                for element in elements[:10]:  # Limit to first 10 items
                    text = element.get_text(strip=True)
                    if len(text) > 50:  # Only include substantial content
                        data['content'].append(text[:500])  # Truncate long content

            return data

        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return None

    def run_scraper(self):
        results = []
        delay = self.config.get('scraping_settings', {}).get('delay_between_requests', 2)

        # Scrape competitor websites
        if self.config.get('websites'):
            print("\n=== Scraping AI Competitor Websites ===")
            for company, url in self.config['websites'].items():
                print(f"Scraping {company}: {url}")
                data = self.scrape_website(url, company)
                if data:
                    results.append(data)
                time.sleep(delay)

        # Scrape tech news websites for AI content
        if self.config.get('tech_news_websites'):
            print("\n=== Scraping Tech News Websites for AI Content ===")
            for source, url in self.config['tech_news_websites'].items():
                print(f"Scraping {source}: {url}")
                data = self.scrape_tech_news(url, source)
                if data:
                    results.append(data)
                time.sleep(delay)

        return results

    def save_results(self, results):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reports/scraper_results_{timestamp}.json"

        os.makedirs('reports', exist_ok=True)

        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"Results saved to {filename}")
        return filename

    def generate_report(self, results):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        report_date = datetime.now().strftime('%Y-%m-%d')

        report = f"# AI News & Competitor Intelligence Report - {report_date}\n\n"
        report += f"Generated on: {timestamp}\n\n"

        # Separate competitor and news results
        competitor_results = [r for r in results if 'company' in r]
        news_results = [r for r in results if 'articles' in r]

        if competitor_results:
            report += "## AI Competitor Updates\n\n"
            for result in competitor_results:
                report += f"### {result['company']}\n"
                report += f"**Source:** {result['url']}\n"
                report += f"**Scraped:** {result['scraped_at']}\n\n"

                if result['content']:
                    report += "**Key Content:**\n"
                    for content in result['content'][:5]:  # Top 5 content items
                        report += f"- {content}\n"
                else:
                    report += "No significant content extracted.\n"

                report += "\n---\n\n"

        if news_results:
            report += "## Latest AI News from Tech Media\n\n"
            for result in news_results:
                report += f"### {result['source']}\n"
                report += f"**Source:** {result['url']}\n"
                report += f"**Scraped:** {result['scraped_at']}\n\n"

                if result['articles']:
                    report += "**Recent AI Articles:**\n"
                    for article in result['articles'][:10]:  # Top 10 articles
                        if article['link']:
                            report += f"- [{article['title']}]({article['link']})\n"
                        else:
                            report += f"- {article['title']}\n"
                else:
                    report += "No AI-related articles found.\n"

                report += "\n---\n\n"

        filename = f"reports/ai_news_report_{report_date}.md"
        with open(filename, 'w') as f:
            f.write(report)

        print(f"Report generated: {filename}")
        return filename

if __name__ == "__main__":
    tracker = AINewsTracker()
    results = tracker.run_scraper()

    if results:
        tracker.save_results(results)
        tracker.generate_report(results)
    else:
        print("No results to process.")