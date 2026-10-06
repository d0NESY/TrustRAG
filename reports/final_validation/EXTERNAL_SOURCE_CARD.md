# 外部数据来源与用途

来源为公开 SQuAD2 development set：<https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v2.0.json>。下载成功、4,370,528 字节，35 个原始文章家族；原始文件及 SHA256 保存在 experiments/final_validation/external/。

评测保留原生人类问题、answer offsets、accepted answer aliases 与 impossible labels。未通过 Gemma2 或 Codex 生成问题/gold；独立项目人工复核仍未完成。

抽样规则在推理前固定：原文章顺序首15个具有合格段落的家族，每家族首个至少3个 positive/2个 impossible 的段落，原顺序首3正例/2负例，共75问。不是基于成绩选择，也不按文本长度过滤。

原文为真实 Wikipedia 摘录；为沿用不变 PDF pipeline，原段落完整忠实转换成 PDF，并核对正文与 gold span、页码及全部15页渲染。PDF 文件是本项目格式转换，不声称是原始官网发布的 PDF，也没有编造政策内容。

原文、原始 annotation 与 article title 可在 source_contexts.json、squad_v2_dev.json 和 questions.jsonl 中查阅。Wikipedia 原文章入口采用 `https://en.wikipedia.org/wiki/<native_title>`；本评测正文以 SQuAD2 固定发布快照为准，不使用今天网页的更新版本代替。

公开数据卡来源：<https://huggingface.co/datasets/rajpurkar/squad_v2>；其原始 Markdown 保存于 public_dataset_card.md，许可与数据作者信息以该卡及原发布页面为准。引用 Wikipedia contributors 和 SQuAD2 发布者 Rajpurkar 等；保留数据来源和署名，不将自然文档内容归为项目原创。

限制：只有15个短摘录、每文档5问；不是完整自然企业政策。public benchmark 可能存在预训练暴露，native impossible annotations 原本只针对所配单段文本，多文档全局有效性尚未独立复核。检索指标已饱和，不能据此宣称大规模困难检索或端到端生产泛化。

外部检索完整运行；生成/judge 在原 CUDA runtime 初始化时失败，按原服务配置重启仍失败，状态 BLOCKED。绝不将未测生成指标填写为成功或拒答。
