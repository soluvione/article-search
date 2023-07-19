from functions import *

article = ''

if __name__ == '__main__':
    file = open('test_scraper.py', 'w')

    file.write(get_imports())
    file.write(get_web_driver())

    val = input('Giriş URLsi: ')
    file.write(get_base_url(val))

    # region Try - Catch Clause
    file.write(start_try_catch())

    while True:
        val = input('Komut Giriniz: ')

        if val.startswith('f'):
            vals = val.split(' ')
            file.write(find_elements(vals[1], vals[2]))
            break

        file.write(click_element(val.split(' ')[1]))

    val = input('ASC/DESC belirtiniz: ')
    if val.upper() == 'DESC':
        file.write('contents = element.find_elements(By.TAG_NAME, \'a\')\n')
        file.write('    print(contents[0].get_attribute(\'href\'))\n\n')
    else:
        file.write('contents = element.find_elements(By.TAG_NAME, \'a\')\n')
        file.write('    print(contents[len(contents)-1].get_attribute(\'href\'))\n\n')

    file.write(end_try_catch())
    # endregion
