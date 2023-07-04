# import time
#
# from selenium import webdriver
# import re
#
# # Your URLs string
# urls_string = ('https://actamedica.org/index.php/actamedica, '
#  'https://beslenmevediyetdergisi.org/index.php/bdd, https://eurjther.com/index.php/home, '
#  'https://experimentalbiomedicalresearch.com/ojs/index.php/ebr, https://medicaljournal.gazi.edu.tr/index.php/GMJ, '
#  'https://ijcmbs.com/index.php/ijcmbs, https://jointdrs.org/current-issue, https://www.jabsonline.org/index.php/jabs/issue/archive, '
#  'https://www.jsoah.com/index.php/jsoah/issue/archive, https://www.medscidiscovery.com/index.php/msd/issue/archive, '
#  'https://natprobiotech.com/index.php/natprobiotech, https://www.pbsciences.org/?sec=archive, '
#  'http://journals.iku.edu.tr/sybd/index.php/sybd/issue/archive, http://www.cityhealthj.org/index.php/cityhealthj/issue/archive, '
#  'https://injectormedicaljournal.com/index.php/theinjector/issue/archive, https://www.ulutasmedicaljournal.com/index.php?sec=archive, '
#  'https://www.derleme.gen.tr/index.php/derleme, http://saglikokuryazarligidergisi.com/index.php/soyd/issue/archive')
#
# # Use a regex to extract the URLs from the string
# urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', urls_string)
#
# # Initialize the Chrome driver
# driver = webdriver.Chrome()
#
# # Open the first URL
# driver.get(urls[0])
#
# # For remaining URLs, open each in a new tab
# for url in urls[1:]:
#     # Open a new tab
#     driver.execute_script("window.open('');")
#
#     # Switch to the new tab
#     driver.switch_to.window(driver.window_handles[-1])
#
#     # Open URL in new tab
#     driver.get(url)
#
# # After opening all tabs, switch to the first tab
# driver.switch_to.window(driver.window_handles[0])
# time.sleep(6000)
import pandas as pd
import re
from urllib.parse import urlparse

# Your URLs string
urls_string = ('Group: https://www.turkarchotolaryngol.net/archives, URLs: https://www.turkarchotolaryngol.net/archives, '
 'https://turkjanaesthesiolreanim.org/en/archive-1710, https://www.turkjorthod.org/archives, https://www.turkosteoporozdergisi.org/archives, '
 'https://viralhepatitisjournal.org/archives, https://www.adlitipbulteni.com/index.php/atb, https://www.ankaratipfakultesimecmuasi.net/, '
 'https://journal.archepilepsy.org/, https://www.behmedicalbulletin.org/, https://www.bezmialemscience.org/archives, https://cyprusjmedsci.com/, '
 'https://www.caybdergi.com/, https://www.dirjournal.org/, https://eajem.com/, https://eurarchmedres.org/, https://www.eurjbreasthealth.com/, '
 'https://ejgg.org/, https://gulhanemedj.org/, https://www.guncelpediatri.com/, https://www.hasekidergisi.com/, https://istanbulmedicaljournal.org/, '
 'https://www.jtad.org/archives, https://www.jtgga.org/archives, https://jurolsurgery.org/archives, https://meandrosmedicaljournal.org/archives/, '
 'https://bakirkoymedj.org/archives/, https://mirt.tsnmjournals.org/archives/, https://namikkemalmedj.com/archives, '
 'https://nukleertipseminerleri.org/archives/, https://jpedres.org/archives, https://www.jtss.org/archives, https://tjoddergisi.org/archives, '
 'https://www.turkjps.org/archives, https://www.oftalmoloji.org/archives, https://www.turkishjic.org/archives, '
 'https://www.turkiyeparazitolderg.org/archives, https://raeddergisi.org/archives, https://uroonkolojibulteni.com/archives')

# Use a regex to extract the URLs from the string
urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', urls_string)

# Remove duplicates and convert to DataFrame
urls_df = pd.DataFrame(list(set(urls)), columns=['URLs'])

# Extract root domain from each URL
urls_df['URLs'] = urls_df['URLs'].apply(lambda url: urlparse(url).netloc)

# Write to Excel
urls_df.to_excel('urls.xlsx', index=False)

# Assuming that the original Excel file is 'original.xlsx' and
# the first column contains the journal names and the second column contains the URLs.
original_df = pd.read_excel('Book1.xlsx', header=None, names=['Names', 'URLs'])

# Extract root domain from each URL
original_df['URLs'] = original_df['URLs'].apply(lambda url: urlparse(url).netloc)

# Merge the original DataFrame with the new DataFrame based on URLs
merged_df = pd.merge(original_df, urls_df, how='inner', on='URLs')

# Write the merged DataFrame to a new Excel file
merged_df.to_excel('merged.xlsx', index=False)
