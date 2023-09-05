Türkiye Klinikleri Article Search

Önemli Not!
Proje bir sanal makineye klonlanacağında aşağıdaki PATH bilgilerine uygun şekilde dosya yapısı oluşturulmalıdır:
Webdriver Konumu: "/home/ubuntu/driver/chromedriver-linux64/chromedriver"
Proje konumu: "/home/ubuntu/article-search"
Ardından .gitignore dosyasında bulunan config ve credential dosyaları elle ilgili yerlerde oluşturulmalıdır

@Callers Paketi ve Modülleri
Scriptleri çalıştıracak olan ve sistem üzerinden çalıştırılması otomasyona bağlanacak olan modüllerdir.
Yalnızca bu modüller scraperları çağıracak olup, takribi 30 scraper için 1 adet caller oranı uygun gözükmektedir.

@Classes Paketi
Projede kullanılan classları barındırıyor.

@Common Paketi
Projede ortak kullanılan sabitler, helperlar ve servisleri barındırıyor.

@Deprecated
Kliniklerin sayfasından 600 dergiye ait veriyi çekmek için yazdığım scripti barındırıyor.

@Project Files
Excel dosyaları ve diğer formatta dosyaları barındırıyor. Bu dosyalar modüllerde kullanılmamakta.

@Sandbox
Dergi PDFlerini parselayıp text ve font verilerini rahat almak için yazdığım bağımsız modül.

@Scrapers
Her bir dergiye ait yazılmış scraperları ve dergilere ait json dosyalarını barındıran paket.
Her bir derginin kendi adını taşıyan bir dosyası bulunmakta, bu dosyada kendi adını taşıyan bir script bulunmakta.
Bu scriptler derginin bilgilerini içermekte olup her dergi için ayarlanmaktadır.
Bütün kıyas, indirme ve parselama işlemleri bu bireysel scraperlar üzerinden gerçekleşmektedir.





