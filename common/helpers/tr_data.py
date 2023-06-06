def get_turkish_data(driver, language_tabs):
    # GO TO THE TURKISH TAB
    language_tabs[0].click()
    time.sleep(0.7)
    tr_article_element = driver.find_element(By.ID, 'article_tr')
    article_title_tr = tr_article_element.find_element(By.CSS_SELECTOR, '.article-title').get_attribute(
        'innerText').strip()
    abstract_tr = abstract_formatter(tr_article_element.find_element(By.CSS_SELECTOR,
                                                                     'div.article-abstract.data-section') \
                                     .find_element(By.TAG_NAME, 'p').get_attribute('innerText'), "tr")
    return article_title_tr, abstract_tr
