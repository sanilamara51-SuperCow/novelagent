# 北魏主线史料深挖 V2

适配设定主线：借鸡生蛋 -> 河阴之变 -> 明光殿刺杀 -> 高欢接盘

## A. 三幕对应史料包

- 第一幕（借鸡生蛋：依附尔朱、吞并流民武装）
  - 资治通鉴 卷151, 卷152
  - 魏书 卷74（尔朱荣传）
  - 北齐书 卷1（神武帝上）

- 第二幕（河阴之变：清洗百官、影子内阁）
  - 资治通鉴 卷152
  - 魏书 卷10（孝庄纪）
  - 魏书 卷74（尔朱荣传）
  - 洛阳伽蓝记 卷1

- 第三幕（明光殿刺杀与接盘）
  - 资治通鉴 卷154, 卷155, 卷156
  - 魏书 卷10, 卷11, 卷75
  - 北齐书 卷1, 卷2
  - 北史 卷5, 卷6, 卷48

## B. 人物锚点（可直接打标签）

1) 尔朱荣
- 魏书 卷74 列传第六十二 尔朱荣传
  - https://zh.wikisource.org/wiki/魏書/卷七十四
  - https://ctext.org/wiki.pl?if=gb&chapter=598331
- 北史 卷48 列传第三十六（尔朱系统）
  - https://ctext.org/wiki.pl?chapter=1934881&if=gb

2) 尔朱兆 / 尔朱世隆 / 尔朱度律 / 尔朱天光
- 魏书 卷75 列传第六十三（尔朱兆等）
  - https://zh.wikisource.org/wiki/魏書/卷七十五
- 北史 卷48
  - https://ctext.org/wiki.pl?chapter=1934881&if=gb

3) 孝庄帝 元子攸
- 魏书 卷10 帝纪第十 孝庄纪
  - https://zh.wikisource.org/wiki/魏書/卷十
- 北史 卷5 魏本纪第五
  - https://ctext.org/wiki.pl?chapter=809514&if=gb

4) 高欢
- 北齐书 卷1 帝纪第一 神武上
  - https://zh.wikisource.org/wiki/北齊書/卷一
- 北齐书 卷2 帝纪第二 神武下
  - https://zh.wikisource.org/wiki/北齊書/卷二
- 北史 卷6 齐本纪上第六
  - https://ctext.org/wiki.pl?if=gb&res=593209

5) 侯刚 / 侯景（分离建索引）
- 侯刚：魏书 卷93 列传恩幸第八十一
  - https://zh.wikisource.org/wiki/魏書/卷九十三
- 侯景：魏书 列传第六十三（ctext索引）
  - https://ctext.org/datawiki.pl?if=gb&res=232000

6) 葛荣
- 资治通鉴 卷151-152（起事到覆灭）
  - https://zh.wikisource.org/wiki/資治通鑑/卷151
  - https://zh.wikisource.org/wiki/資治通鑑/卷152
- 魏书 卷74（尔朱荣平葛荣）
  - https://zh.wikisource.org/wiki/魏書/卷七十四

7) 元天穆 / 陈庆之 / 元颢（承压角色）
- 元天穆：魏书卷74、北史卷48
  - https://ctext.org/wiki.pl?if=gb&chapter=598331
- 陈庆之、元颢：资治通鉴 卷153
  - https://zh.wikisource.org/wiki/資治通鑑/卷153

8) 贺拔岳 / 宇文泰（后继政治地震）
- 建议主检：资治通鉴 卷156（北魏分裂前后）
  - https://zh.wikisource.org/wiki/資治通鑑/卷156
- 次检：北史相关列传（入库前再逐章核卷）

## C. 事件锚点（523-534）

- 523-526 六镇起义背景 -> 通鉴卷151 / 魏书卷9
- 526-528 葛荣起兵与坐大 -> 通鉴卷151-152
- 528 河阴之变 -> 通鉴卷152 / 魏书卷10 / 魏书卷74
- 528 尔朱荣灭葛荣 -> 通鉴卷152 / 魏书卷74
- 529 元颢-陈庆之入洛 -> 通鉴卷153
- 530 明光殿之变（刺杀尔朱荣） -> 通鉴卷154 / 魏书卷10
- 530-531 尔朱系反扑与政变连锁 -> 魏书卷11 / 魏书卷75 / 通鉴卷155
- 531 孝庄帝被弑 -> 北史卷5 / 通鉴卷155
- 531 高欢起兵 -> 通鉴卷155 / 北齐书卷1
- 532 韩陵之战 -> 通鉴卷155 / 北齐书卷2
- 533 尔朱余部清算 -> 通鉴卷156
- 534 北魏分裂 -> 通鉴卷156

## D. 可脚本化抓取接口（重点）

1) Wikisource API
- `https://zh.wikisource.org/w/api.php?action=parse&page=魏書/卷七十五&prop=wikitext&format=json`

2) Wikisource export
- `https://ws-export.wmcloud.org/?lang=zh&format=txt&page=資治通鑑/卷154`

3) ctext章节页
- `https://ctext.org/wiki.pl?if=gb&chapter=598331`

4) ctext API文档
- `https://ctext.org/tools/api`

5) GitHub镜像
- `https://github.com/yuanshiming/Twenty-Four-Histories`
- `https://github.com/JY0284/zizhitongjian`

## E. 入库标签规范（建议直接采用）

- person_tags: `erzhurong`, `xiaozhuang`, `gaohuan`, `ge_rong`, `erzhu_zhao`, `erzhu_shilong`, `yuan_tianmu`, `chen_qingzhi`, `yuan_hao`
- event_tags: `six_garrisons_revolt`, `ge_rong_revolt`, `heyin_incident`, `mingguang_assassination`, `hanling_battle`, `xiazhuang_killed`, `northern_wei_split`
- phase_tags: `phase1_egg`, `phase2_heyin`, `phase3_takeover`

## F. 下一轮可继续深挖位点

- 梁书/南史中陈庆之与北魏政局交叉段（补外视角）
- 北史中贺拔岳、宇文泰细传（补东西魏分裂过渡）
- 通鉴纪事本末对应专题卷（补结构化叙事检索）
