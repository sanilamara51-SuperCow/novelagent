# 北魏主线史料深挖索引（RAG）

主线：借鸡生蛋 -> 河阴之变(528) -> 明光殿之变(530) -> 高欢接盘(531-534)

## 一、核心章节（优先入库）

1. 魏书 卷十 帝纪第十 孝庄纪  
   URL: https://zh.wikisource.org/wiki/魏書/卷十

2. 魏书 卷七十四 列传第六十二 尔朱荣传  
   URL: https://zh.wikisource.org/wiki/魏書/卷七十四

3. 魏书 卷九十三 列传恩幸第八十一（含侯刚）  
   URL: https://zh.wikisource.org/wiki/魏書/卷九十三

4. 资治通鉴 卷151（六镇起义、葛荣崛起背景）  
   URL: https://zh.wikisource.org/wiki/資治通鑑/卷151

5. 资治通鉴 卷152（河阴之变、尔朱荣立孝庄帝）  
   URL: https://zh.wikisource.org/wiki/資治通鑑/卷152

6. 资治通鉴 卷154（明光殿之变，孝庄帝刺杀尔朱荣）  
   URL: https://zh.wikisource.org/wiki/資治通鑑/卷154

7. 资治通鉴 卷155（高欢起兵、韩陵之战）  
   URL: https://zh.wikisource.org/wiki/資治通鑑/卷155

8. 资治通鉴 卷156（尔朱氏余波、北魏分裂前夜）  
   URL: https://zh.wikisource.org/wiki/資治通鑑/卷156

9. 北齐书 卷一 神武帝上（高欢早期）  
   URL: https://zh.wikisource.org/wiki/北齊書/卷一

10. 北齐书 卷二 神武帝下（高欢巩固）  
    URL: https://zh.wikisource.org/wiki/北齊書/卷二

11. 北史 卷五（孝庄帝）  
    URL: https://ctext.org/wiki.pl?chapter=809514&if=gb

12. 北史 卷四十八（尔朱荣、尔朱兆、尔朱世隆系统）  
    URL: https://ctext.org/wiki.pl?chapter=1934881&if=gb

13. 洛阳伽蓝记 卷一（永宁寺、洛阳政局）  
    URL: https://zh.wikisource.org/wiki/洛陽伽藍記/卷一

14. 洛阳伽蓝记 卷四（宣忠寺、明光殿相关背景）  
    URL: https://zh.wikisource.org/wiki/洛陽伽藍記/卷四

## 二、人物映射（用于检索标签）

- 尔朱荣: 魏书卷74 / 北史卷48 / 通鉴卷152,154
- 孝庄帝 元子攸: 魏书卷10 / 北史卷5 / 通鉴卷152,154
- 高欢: 北齐书卷1-2 / 北史齐本纪上 / 通鉴卷155
- 侯刚: 魏书卷93
- 葛荣: 通鉴卷151-152，魏书卷74中有被平定记述
- 尔朱兆、尔朱世隆、元天穆: 北史卷48、魏书卷74、通鉴卷154-156
- 陈庆之、元颢: 通鉴卷153（承接528-530局势）

## 三、可机读来源（下载优先级）

1) 维基文库（高优先）
- 可直接按卷抓取 HTML，再清洗为 UTF-8 txt
- API: https://zh.wikisource.org/w/api.php

2) ctext（高优先）
- 便于按章节定位、做交叉校对
- 示例：魏书卷74 https://ctext.org/wiki.pl?if=gb&chapter=389991

3) GitHub 开源语料（高优先）
- Twenty-Four-Histories: https://github.com/yuanshiming/Twenty-Four-Histories
- zizhitongjian: https://github.com/JY0284/zizhitongjian

4) 备份镜像（中优先）
- Internet Archive 魏书检索: https://archive.org/search?query=魏书

## 四、入库建议（和你当前设定强绑定）

- 第一批必放：通鉴152/154/155 + 魏书10/74 + 北齐书1
- 第二批补强：北史48、通鉴151/156、伽蓝记1/4
- Chunk metadata 至少保留：work, juan, person_tags, event_tags, year_range
- event_tags 建议固定词表：六镇起义, 葛荣起义, 河阴之变, 明光殿之变, 韩陵之战, 东西魏分裂

## 五、人物深挖锚点（第一批扩展）

备注：你的设定里“侯刚”建议双向检索 `侯刚` 与 `侯景`，避免史实映射漏召回。

- 尔朱荣 -> 魏书 卷74 列传第六十二 尔朱荣传  
  URL: https://ctext.org/wiki.pl?if=gb&chapter=598331
- 尔朱荣 -> 北史 卷48 列传第三十六  
  URL: https://ctext.org/wiki.pl?chapter=1934881&if=gb
- 孝庄帝 元子攸 -> 魏书 卷10 帝纪第十 孝庄纪  
  URL: https://zh.wikisource.org/wiki/魏書/卷十
- 孝庄帝 元子攸 -> 北史 卷5 魏本纪第五  
  URL: https://ctext.org/wiki.pl?chapter=809514&if=gb
- 高欢 -> 北齐书 卷1 帝纪第一 神武上  
  URL: https://zh.wikisource.org/wiki/北齊書/卷一
- 高欢 -> 北齐书 卷2 帝纪第二 神武下  
  URL: https://zh.wikisource.org/wiki/北齊書/卷二
- 高欢 -> 北史 卷6 齐本纪上第六  
  URL: https://ctext.org/wiki.pl?if=gb&res=593209
- 侯刚 -> 魏书 卷93 列传恩幸第八十一  
  URL: https://zh.wikisource.org/wiki/魏書/卷九十三
- 侯景 -> 魏书 列传第六十三（可与侯刚分开建标签）  
  URL: https://ctext.org/datawiki.pl?if=gb&res=232000
- 葛荣 -> 资治通鉴 卷151-152（起兵与败亡）  
  URL: https://zh.wikisource.org/wiki/資治通鑑/卷151
- 葛荣 -> 魏书 卷74 尔朱荣传（被平定叙事）  
  URL: https://zh.wikisource.org/wiki/魏書/卷七十四
- 尔朱兆 -> 北史 卷48（尔朱系统传记）  
  URL: https://ctext.org/wiki.pl?chapter=1934881&if=gb
- 尔朱世隆 -> 北史 卷48  
  URL: https://ctext.org/wiki.pl?chapter=1934881&if=gb
- 元天穆 -> 魏书 卷74 / 北史 卷48  
  URL: https://ctext.org/wiki.pl?chapter=598331&if=gb
- 陈庆之 -> 资治通鉴 卷153（元颢入洛段）  
  URL: https://zh.wikisource.org/wiki/資治通鑑/卷153
- 元颢 -> 资治通鉴 卷153  
  URL: https://zh.wikisource.org/wiki/資治通鑑/卷153

## 六、事件深挖年表（523-534，便于RAG标签）

- 523-525 六镇起义发酵 -> 资治通鉴 卷151  
  URL: https://zh.wikisource.org/wiki/資治通鑑/卷151
- 526 葛荣坐大 -> 资治通鉴 卷151  
  URL: https://zh.wikisource.org/wiki/資治通鑑/卷151
- 528 河阴之变 -> 资治通鉴 卷152 / 魏书卷10 / 魏书卷74  
  URL: https://zh.wikisource.org/wiki/資治通鑑/卷152
- 528 尔朱荣破葛荣 -> 资治通鉴 卷152 / 魏书卷74  
  URL: https://zh.wikisource.org/wiki/資治通鑑/卷152
- 529 元颢-陈庆之线入洛 -> 资治通鉴 卷153  
  URL: https://zh.wikisource.org/wiki/資治通鑑/卷153
- 530 明光殿之变（刺杀尔朱荣） -> 资治通鉴 卷154 / 魏书卷10  
  URL: https://zh.wikisource.org/wiki/資治通鑑/卷154
- 531 孝庄帝被弑（尔朱兆系） -> 北史卷5 / 资治通鉴卷155  
  URL: https://ctext.org/wiki.pl?chapter=809514&if=gb
- 531 高欢起兵反尔朱 -> 资治通鉴 卷155 / 北齐书卷1  
  URL: https://zh.wikisource.org/wiki/資治通鑑/卷155
- 532 韩陵之战 -> 资治通鉴 卷155 / 北齐书卷2  
  URL: https://zh.wikisource.org/wiki/資治通鑑/卷155
- 533 尔朱余部覆灭 -> 资治通鉴 卷156  
  URL: https://zh.wikisource.org/wiki/資治通鑑/卷156
- 534 北魏分裂前后 -> 资治通鉴 卷156  
  URL: https://zh.wikisource.org/wiki/資治通鑑/卷156

## 七、下载接口模板（可直接写脚本）

1) Wikisource API（页面正文）

`https://zh.wikisource.org/w/api.php?action=parse&page=魏書/卷十&prop=wikitext&format=json`

2) Wikisource Export（整页导出）

`https://ws-export.wmcloud.org/?lang=zh&format=txt&page=魏書/卷十`

3) ctext 章节页（HTML抓取）

`https://ctext.org/wiki.pl?if=gb&chapter=598331`

4) ctext API（需按其规则与权限调用，建议保留离线镜像）

`https://ctext.org/api/tools` (文档入口)

5) GitHub离线语料镜像

- https://github.com/yuanshiming/Twenty-Four-Histories
- https://github.com/JY0284/zizhitongjian
