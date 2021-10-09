爬虫通过读取表格来工作，表格内容一般如下:

|学院名|网址|教师|姓名|职称|学系名|研究领域|
|-|-|-|-|-|-|-|
|财务管理与会计研究院|https://ifas.xmu.edu.cn/szdw/hjx.htm<br>https://ifas.xmu.edu.cn/szdw/hjx/1.htm|//div[@class="course-detail"]/a|./../h4//text()|./../p[last()]//text()|//div[@class="container"]/h1//text()||
---
+ <b>学院名:</b> 此列一般直接填学院名，可以在末尾以"=>"连接学系名，例如: <code>数理学院=>数学系</code>。如果之后的学系名一栏不为空，则此处的学系名之后将被覆盖。
+ <b>网址:</b> 可以有多个网址，以换行符隔开，爬虫会执行一次去重操作。如必要可以使用列表生成式生成多个网址，例如: <code>['https://www.med.cam.ac.uk/staff/division/infectious-diseases/?fwp_paged={0}'.format(i) for i in range(2,11)]</code>
+ <b>教师:</b> 