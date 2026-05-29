from __future__ import annotations

from pathlib import Path


SRC = Path("docs/exam/gaoxiang_gemini_source.html")
OUT = Path("docs/exam/高项-gemini-案例计算扩展版.html")


expanded_css = """
<style>
.codex-ext { --ce-blue:#1d4ed8; --ce-red:#dc2626; --ce-green:#15803d; --ce-amber:#b45309; --ce-bg:#f8fafc; --ce-panel:#ffffff; --ce-line:#cbd5e1; --ce-text:#1e293b; --ce-muted:#64748b; margin:32px auto; max-width:1180px; color:var(--ce-text); }
.codex-ext * { box-sizing:border-box; }
.codex-ext .ce-hero { background:linear-gradient(135deg,#eff6ff,#fff7ed); border:1px solid var(--ce-line); border-radius:14px; padding:26px; margin:24px 0; }
.codex-ext h1 { margin:0 0 8px; font-size:30px; color:#0f172a; }
.codex-ext h2 { margin:30px 0 12px; padding-left:10px; border-left:5px solid var(--ce-blue); font-size:24px; color:#0f172a; }
.codex-ext h3 { margin:18px 0 8px; font-size:18px; color:#0f172a; }
.codex-ext p { margin:8px 0; line-height:1.75; }
.codex-ext .ce-menu { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:10px; margin-top:16px; }
.codex-ext .ce-menu a { display:block; padding:10px 12px; border:1px solid var(--ce-line); border-radius:8px; background:white; color:#1d4ed8; text-decoration:none; font-weight:600; }
.codex-ext .ce-note { background:#fffbeb; border:1px solid #f59e0b; border-radius:10px; padding:12px 14px; margin:14px 0; }
.codex-ext .ce-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(310px,1fr)); gap:14px; }
.codex-ext .ce-card { background:var(--ce-panel); border:1px solid var(--ce-line); border-radius:12px; padding:15px; box-shadow:0 1px 2px rgba(15,23,42,.04); }
.codex-ext .ce-card h3 { display:flex; align-items:center; justify-content:space-between; gap:8px; border-bottom:1px solid #e2e8f0; padding-bottom:7px; }
.codex-ext .ce-tag { font-size:12px; color:white; background:var(--ce-blue); border-radius:999px; padding:2px 8px; white-space:nowrap; }
.codex-ext .ce-tag.red { background:var(--ce-red); } .codex-ext .ce-tag.green { background:var(--ce-green); } .codex-ext .ce-tag.amber { background:var(--ce-amber); }
.codex-ext ul, .codex-ext ol { padding-left:22px; } .codex-ext li { margin:5px 0; line-height:1.68; }
.codex-ext table { width:100%; border-collapse:collapse; margin:12px 0 18px; background:white; }
.codex-ext th, .codex-ext td { border:1px solid var(--ce-line); padding:10px; vertical-align:top; line-height:1.65; }
.codex-ext th { background:#e0f2fe; color:#0f172a; text-align:left; }
.codex-ext .ce-answer { background:#f1f5f9; border-left:4px solid var(--ce-green); padding:10px 12px; border-radius:8px; margin-top:8px; }
.codex-ext .ce-wrong { color:#b91c1c; font-weight:700; }
.codex-ext .ce-right { color:#166534; font-weight:700; }
.codex-ext code { background:#e2e8f0; border-radius:5px; padding:1px 5px; }
.codex-ext .ce-formula { font-family:Consolas, 'Courier New', monospace; background:#0f172a; color:#e2e8f0; border-radius:10px; padding:12px; overflow:auto; }
.codex-ext .ce-steps { counter-reset:step; list-style:none; padding-left:0; }
.codex-ext .ce-steps li { position:relative; padding-left:42px; margin:10px 0; }
.codex-ext .ce-steps li::before { counter-increment:step; content:counter(step); position:absolute; left:0; top:0; width:28px; height:28px; border-radius:50%; background:#1d4ed8; color:white; display:flex; align-items:center; justify-content:center; font-weight:700; }
@media print { .codex-ext { max-width:none; } .codex-ext .ce-card, .codex-ext table { break-inside:avoid; } }
</style>
"""


expanded_body = """
<section class="codex-ext" id="codex-case-calc">
  <div class="ce-hero">
    <h1>案例分析与计算题扩展版</h1>
    <p>本扩展章是在原 HTML 基础上增加的“下午案例分析 + 计算题”专项。内容按近年案例真题高频题型抽象整理：找错改错、知识点背诵、万能答题句、常见错误标准答案、计算公式与解题步骤。</p>
    <div class="ce-note"><strong>使用方法：</strong>案例题先背“万能答题骨架”和“常见错误-纠正措施”；计算题先背公式，再按“列数据、套公式、写判断、给措施”的顺序作答。</div>
    <div class="ce-menu">
      <a href="#ce-trend">近年案例高频画像</a>
      <a href="#ce-universal">找错改错万能句</a>
      <a href="#ce-errors">常见错误标准答案</a>
      <a href="#ce-knowledge">案例知识点背诵</a>
      <a href="#ce-case-practice">案例题型模板</a>
      <a href="#ce-calc-formulas">计算题公式</a>
      <a href="#ce-calc-method">计算题答题技巧</a>
      <a href="#ce-sources">依据说明</a>
    </div>
  </div>

  <h2 id="ce-trend">一、近 8 年案例分析高频画像</h2>
  <table>
    <thead><tr><th>高频方向</th><th>常见题型</th><th>高频采分词</th><th>答题提醒</th></tr></thead>
    <tbody>
      <tr><td>变更控制</td><td>找错、补流程、判断谁批准</td><td>变更请求、变更日志、影响分析、CCB、更新基准、通知干系人</td><td>影响基准的变更不能口头执行，项目经理通常不能个人拍板。</td></tr>
      <tr><td>范围/WBS/需求</td><td>范围蔓延、WBS 不完整、需求追踪</td><td>范围说明书、WBS、WBS 词典、范围基准、需求跟踪矩阵、验收标准</td><td>新增需求要走变更；WBS 是可交付成果导向，不是简单活动清单。</td></tr>
      <tr><td>进度网络图</td><td>关键路径、总工期、总时差/自由时差、赶工快速跟进</td><td>ES、EF、LS、LF、TF、FF、关键路径、进度基准、SPI、SV</td><td>关键路径要写完整路径和工期；压缩工期要说明成本/风险影响。</td></tr>
      <tr><td>挣值管理</td><td>PV/EV/AC 计算，判断进度成本状态，预测 EAC/ETC</td><td>CV、SV、CPI、SPI、EAC、ETC、VAC、TCPI</td><td>算完必须写“超支/节约、落后/超前、后续压力”。</td></tr>
      <tr><td>风险管理</td><td>识别风险、补登记册、应对策略</td><td>风险登记册、概率影响矩阵、风险责任人、触发条件、应急计划、储备</td><td>风险未发生，问题已发生；威胁和机会策略要分开。</td></tr>
      <tr><td>干系人/沟通</td><td>参与不足、沟通混乱、冲突升级</td><td>干系人登记册、参与矩阵、沟通管理计划、会议纪要、问题日志、升级机制</td><td>沟通计划要有对象、内容、频率、渠道、责任人和反馈。</td></tr>
      <tr><td>质量管理</td><td>验收失败、缺陷多、质量活动缺失</td><td>质量管理计划、质量测量指标、质量审计、测试、评审、缺陷闭环</td><td>控制质量不等于确认范围；质量要前置，不能只靠最后验收。</td></tr>
      <tr><td>采购合同</td><td>合同类型选择、招投标流程、供应商问题</td><td>SOW、采购文件、评标标准、合同类型、采购审计、索赔、分包审批</td><td>范围清楚偏总价，范围不清偏成本补偿，工作量不清且需快速推进可用工料。</td></tr>
    </tbody>
  </table>

  <h2 id="ce-universal">二、找错改错万能回答句</h2>
  <div class="ce-grid">
    <div class="ce-card"><h3>1. 找错题总模板 <span class="ce-tag red">必背</span></h3>
      <p><span class="ce-wrong">错误：</span>没有计划、没有基准、没有台账、没有责任人、没有影响分析、没有审批、没有更新文档、没有通知干系人、没有跟踪闭环。</p>
      <div class="ce-answer"><strong>万能改法：</strong>应制定相应管理计划，建立登记册/日志/矩阵，明确责任人和流程，对问题或变更进行影响分析，经授权审批后实施，更新项目管理计划和相关文件，通知受影响干系人，并持续跟踪验证效果。</div>
    </div>
    <div class="ce-card"><h3>2. 问“项目经理应该怎么做” <span class="ce-tag">模板</span></h3>
      <ol>
        <li>先了解事实，收集数据和相关文件。</li>
        <li>识别受影响干系人，分析真实诉求。</li>
        <li>评估对范围、进度、成本、质量、资源、风险、采购和干系人的影响。</li>
        <li>形成备选方案，必要时召开专题会或提交 CCB。</li>
        <li>批准后更新计划、基准、日志、登记册和沟通内容。</li>
        <li>执行、监督、验收，并沉淀经验教训。</li>
      </ol>
    </div>
    <div class="ce-card"><h3>3. 问“有哪些问题” <span class="ce-tag amber">采分词</span></h3>
      <p>未制定或未遵循项目管理计划；需求和范围未确认；WBS 分解不充分；估算依据不足；进度计划未考虑依赖关系；风险识别不足；质量标准不明确；沟通机制缺失；职责不清；采购流程不规范；变更未受控；未进行监控和纠偏。</p>
    </div>
    <div class="ce-card"><h3>4. 问“如何预防再次发生” <span class="ce-tag green">闭环</span></h3>
      <p>补制度、补模板、补评审、补培训、补检查、补审计、补监控指标、补经验教训。答案要体现“过程资产沉淀”，例如更新模板、检查单、风险清单、估算数据库和组织知识库。</p>
    </div>
  </div>

  <h2 id="ce-errors">三、常考错误问题与标准答案</h2>
  <table>
    <thead><tr><th>领域</th><th>题干常见错误</th><th>标准纠正答案</th></tr></thead>
    <tbody>
      <tr><td>启动/章程</td><td>项目未正式立项，项目经理职责不清，关键干系人未授权。</td><td>应制定并批准项目章程，明确项目目标、成功标准、总体需求、主要风险、里程碑、预算、项目经理职责和授权。</td></tr>
      <tr><td>范围</td><td>客户临时加功能，项目组直接开发；验收时双方对范围理解不一致。</td><td>应明确范围说明书、WBS、WBS 词典和验收标准，形成范围基准；新增需求按变更流程处理，并更新需求跟踪矩阵。</td></tr>
      <tr><td>WBS</td><td>WBS 按组织部门或开发活动随意拆，遗漏测试/培训/上线/运维交接。</td><td>WBS 应以可交付成果为导向，覆盖 100% 项目范围，分解到可估算、可分配、可控制的工作包，并配套 WBS 词典。</td></tr>
      <tr><td>进度</td><td>只凭经验排工期，没有网络图；延期后只要求加班。</td><td>应定义活动、排序、估算持续时间，绘制进度网络图，识别关键路径；压缩进度可采用赶工或快速跟进，并评估成本、质量和风险。</td></tr>
      <tr><td>成本</td><td>预算不含应急储备，管理储备混入成本基准；超支后未分析。</td><td>应基于工作包估算汇总成本，加入应急储备形成成本基准；管理储备不纳入成本基准；执行中用挣值分析并采取纠偏措施。</td></tr>
      <tr><td>质量</td><td>只在最后验收，缺陷多；没有质量测量指标。</td><td>应制定质量管理计划和质量测量指标，开展评审、测试、检查、质量审计和缺陷闭环，预防成本优先于失败成本。</td></tr>
      <tr><td>资源/团队</td><td>职责不清，多头负责；关键资源被其他项目占用。</td><td>应制定资源管理计划和 RACI 矩阵，明确 R/A/C/I；通过谈判、预分派、虚拟团队或升级机制获取关键资源。</td></tr>
      <tr><td>沟通</td><td>只口头通知，会议没有纪要，问题无人跟踪。</td><td>应制定沟通管理计划，明确沟通对象、内容、频率、渠道、格式、责任人和反馈机制；会议形成纪要并进入问题日志跟踪。</td></tr>
      <tr><td>干系人</td><td>忽视最终用户和运维人员，导致上线抵触。</td><td>应识别并分类干系人，建立干系人登记册和参与矩阵，对抵制型、高权力高利益干系人制定参与策略。</td></tr>
      <tr><td>风险</td><td>风险发生后才处理，没有责任人和预案。</td><td>应识别风险，建立风险登记册，做概率影响分析，明确责任人、触发条件、应对策略、应急计划和储备。</td></tr>
      <tr><td>采购</td><td>供应商选择只看价格，采购文件不清，分包未审批。</td><td>应制定采购管理计划、SOW 和评标标准，综合技术、质量、成本、风险和资质选择供应商；分包需买方认可并符合法规和合同。</td></tr>
      <tr><td>变更</td><td>变更口头批准，未评估影响，未更新计划和基准。</td><td>应提交书面变更请求，记录变更日志，进行影响分析，提交 CCB 审批，批准后更新基准和文件，通知干系人并跟踪实施。</td></tr>
      <tr><td>配置</td><td>版本混乱，现场使用旧文档或旧代码。</td><td>应识别配置项，进行版本控制、状态记录、配置核实和配置审计，确保交付物和文档一致。</td></tr>
    </tbody>
  </table>

  <h2 id="ce-knowledge">四、案例分析知识点背诵清单</h2>
  <div class="ce-grid">
    <div class="ce-card"><h3>范围与需求 <span class="ce-tag">背诵</span></h3>
      <ul>
        <li>范围基准=项目范围说明书+WBS+WBS 词典。</li>
        <li>需求跟踪矩阵连接需求来源、业务目标、WBS、设计、开发、测试、验收。</li>
        <li>确认范围是正式验收；控制质量是检查成果是否符合质量要求。</li>
        <li>范围蔓延的根因通常是需求未确认、变更未受控、验收标准不清。</li>
      </ul>
    </div>
    <div class="ce-card"><h3>变更控制 <span class="ce-tag red">必背流程</span></h3>
      <p>提出变更请求 → 记录变更日志 → 初审 → 影响分析 → CCB/授权人审批 → 更新计划/基准/文件 → 通知干系人 → 实施变更 → 验证关闭。</p>
      <p>影响分析至少写：范围、进度、成本、质量、资源、风险、采购、干系人。</p>
    </div>
    <div class="ce-card"><h3>风险应对 <span class="ce-tag">必背</span></h3>
      <p><strong>威胁：</strong>上报、规避、转移、减轻、接受。</p>
      <p><strong>机会：</strong>上报、开拓、分享、提高、接受。</p>
      <p><strong>登记册字段：</strong>风险描述、原因、后果、概率、影响、优先级、责任人、触发条件、应对措施、应急计划、状态。</p>
    </div>
    <div class="ce-card"><h3>沟通与干系人 <span class="ce-tag">常考</span></h3>
      <p>干系人参与水平：不了解、抵制、中立、支持、领导。参与矩阵用 C 当前、D 期望。</p>
      <p>沟通渠道数=n(n-1)/2。沟通计划必须包含对象、内容、频率、方式、责任人和反馈。</p>
    </div>
  </div>

  <h2 id="ce-case-practice">五、案例题型模板：题目 + 答案骨架</h2>
  <div class="ce-grid">
    <div class="ce-card"><h3>题型 1：变更找错题 <span class="ce-tag red">高频</span></h3>
      <p><strong>题干抽象：</strong>用户提出新增报表，项目经理认为工作量不大，安排开发人员直接修改，导致延期和成本增加。</p>
      <div class="ce-answer">
        <strong>答题骨架：</strong>
        <ol>
          <li>错误：未提交书面变更请求，未记录变更日志。</li>
          <li>错误：未分析对范围、进度、成本、质量、风险的影响。</li>
          <li>错误：未经 CCB 或授权人审批，项目经理直接安排实施。</li>
          <li>错误：未更新范围基准、进度基准、成本基准和相关项目文件。</li>
          <li>改正：按变更控制流程处理，批准后实施并验证关闭。</li>
        </ol>
      </div>
    </div>
    <div class="ce-card"><h3>题型 2：范围/WBS 找错题 <span class="ce-tag">高频</span></h3>
      <p><strong>题干抽象：</strong>项目组只按开发模块分解 WBS，未包含测试、培训、数据迁移、上线支持，验收时客户认为交付不完整。</p>
      <div class="ce-answer">
        <strong>答题骨架：</strong>WBS 未覆盖 100% 范围；分解不以可交付成果为导向；缺少 WBS 词典和验收标准；未建立需求跟踪矩阵；应补充完整 WBS、明确验收标准并形成范围基准。
      </div>
    </div>
    <div class="ce-card"><h3>题型 3：风险管理题 <span class="ce-tag">高频</span></h3>
      <p><strong>题干抽象：</strong>项目依赖外部接口，接口规范多次变化，团队没有预案，导致联调延期。</p>
      <div class="ce-answer">
        <strong>答题骨架：</strong>未识别外部接口变更风险；未指定风险责任人；未制定应对措施和应急计划；未预留储备；应建立风险登记册，采用概率影响矩阵排序，制定规避/减轻/转移/接受策略，定期监督。
      </div>
    </div>
    <div class="ce-card"><h3>题型 4：沟通干系人题 <span class="ce-tag">高频</span></h3>
      <p><strong>题干抽象：</strong>系统上线后业务人员抵触，认为功能不符合实际工作流程。</p>
      <div class="ce-answer">
        <strong>答题骨架：</strong>未充分识别最终用户；未分析干系人需求和期望；未让用户参与需求确认、原型评审和验收；沟通计划不足；应建立干系人登记册和参与矩阵，针对抵制型干系人开展访谈、培训、试点和反馈闭环。
      </div>
    </div>
  </div>

  <h2 id="ce-calc-formulas">六、计算题公式总表</h2>
  <table>
    <thead><tr><th>题型</th><th>公式</th><th>判断与答题话术</th></tr></thead>
    <tbody>
      <tr><td>沟通渠道</td><td><code>渠道数=n(n-1)/2</code></td><td>新增 1 人会增加原人数 n 条渠道；注意题目问总渠道还是新增渠道。</td></tr>
      <tr><td>三点估算</td><td><code>TE=(O+4M+P)/6；σ=(P-O)/6；方差=σ²</code></td><td>O 乐观，M 最可能，P 悲观；M 权重为 4。</td></tr>
      <tr><td>关键路径</td><td>路径总工期=路径上活动工期之和；总工期=最长路径</td><td>写出完整关键路径和总工期；关键活动 TF 通常为 0。</td></tr>
      <tr><td>六时标</td><td><code>EF=ES+工期；LS=LF-工期；TF=LS-ES=LF-EF；FF=紧后ES最小值-EF</code></td><td>正推取最大，逆推取最小；自由时差不能影响紧后活动最早开始。</td></tr>
      <tr><td>挣值偏差</td><td><code>CV=EV-AC；SV=EV-PV</code></td><td>CV&lt;0 超支，CV&gt;0 节约；SV&lt;0 落后，SV&gt;0 超前。</td></tr>
      <tr><td>挣值指数</td><td><code>CPI=EV/AC；SPI=EV/PV</code></td><td>CPI&lt;1 成本效率差；SPI&lt;1 进度效率差。</td></tr>
      <tr><td>完工估算</td><td><code>EAC=BAC/CPI</code>；非典型：<code>EAC=AC+(BAC-EV)</code></td><td>典型偏差默认继续按当前效率；非典型表示以后按原计划效率。</td></tr>
      <tr><td>尚需估算</td><td><code>ETC=EAC-AC；VAC=BAC-EAC</code></td><td>VAC&lt;0 预计超支，VAC&gt;0 预计节约。</td></tr>
      <tr><td>完工尚需绩效</td><td><code>TCPI=(BAC-EV)/(BAC-AC)</code> 或 <code>(BAC-EV)/(EAC-AC)</code></td><td>TCPI&gt;1 表示剩余工作成本效率要求高，完成压力大。</td></tr>
      <tr><td>决策树 EMV</td><td><code>EMV=Σ(概率×收益或成本)</code></td><td>收益型选大，成本型选小；注意扣除初始投入。</td></tr>
      <tr><td>CPIF 合同</td><td>节约/超支按买卖双方分担比例分配</td><td>先算实际成本与目标成本差额，再按分担比例调整卖方费用，最后检查最高限价/最低费用。</td></tr>
      <tr><td>投资回收期</td><td>静态回收期=累计净现金流由负转正的时间点</td><td>上一年累计未回收额 / 下一年净现金流，加到上一年末。</td></tr>
    </tbody>
  </table>

  <h2 id="ce-calc-method">七、计算题答题思路技巧</h2>
  <div class="ce-grid">
    <div class="ce-card"><h3>挣值题四步法 <span class="ce-tag red">必会</span></h3>
      <ol class="ce-steps">
        <li>先从题干中圈出 PV、EV、AC、BAC。若题目给“计划完成百分比/实际完成百分比”，先换算金额。</li>
        <li>计算 CV、SV、CPI、SPI。</li>
        <li>按题意选择 EAC 公式：典型偏差用 BAC/CPI，非典型用 AC+(BAC-EV)。</li>
        <li>写结论：成本是否超支、进度是否落后、完工是否超预算、后续是否需要纠偏。</li>
      </ol>
      <div class="ce-formula">答题句：CPI=0.8&lt;1，说明成本绩效较差，项目成本超支；SPI=0.9&lt;1，说明进度绩效较差，项目进度落后。应分析偏差原因，采取成本控制和进度纠偏措施。</div>
    </div>
    <div class="ce-card"><h3>网络图题四步法 <span class="ce-tag">必会</span></h3>
      <ol class="ce-steps">
        <li>列出所有从开始到结束的路径。</li>
        <li>计算每条路径工期，最长路径为关键路径。</li>
        <li>正推求 ES/EF，逆推求 LS/LF。</li>
        <li>计算 TF/FF，判断哪些活动可延误、哪些不能延误。</li>
      </ol>
      <p><strong>技巧：</strong>如果题目问“某活动延期 X 天是否影响总工期”，看该活动总时差 TF。X≤TF 不影响总工期；X&gt;TF 影响 X-TF 天。</p>
    </div>
    <div class="ce-card"><h3>决策树题四步法 <span class="ce-tag">常考</span></h3>
      <ol class="ce-steps">
        <li>画出方案、概率分支和收益/成本。</li>
        <li>对每个方案计算 EMV。</li>
        <li>收益型选择 EMV 最大，成本型选择 EMV 最小。</li>
        <li>写明选择理由，并说明风险偏好或非量化因素可作为补充考虑。</li>
      </ol>
    </div>
    <div class="ce-card"><h3>合同计算题技巧 <span class="ce-tag amber">易错</span></h3>
      <ul>
        <li>先区分目标成本、目标费用、实际成本、分担比例、最高限价。</li>
        <li>实际成本小于目标成本：节约；实际成本大于目标成本：超支。</li>
        <li>卖方费用=目标费用 ± 卖方分担额。</li>
        <li>最终付款=实际成本+调整后的卖方费用，但不得超过最高限价。</li>
      </ul>
    </div>
  </div>

  <h2>八、计算题常见扣分点</h2>
  <table>
    <thead><tr><th>扣分点</th><th>避免方法</th></tr></thead>
    <tbody>
      <tr><td>只写公式不写结论</td><td>每道挣值题都写“超支/节约、落后/超前、是否超预算”。</td></tr>
      <tr><td>把 PV、EV、AC 混淆</td><td>PV 是计划该完成的预算价值；EV 是实际完成工作的预算价值；AC 是实际花费。</td></tr>
      <tr><td>关键路径只写工期不写路径</td><td>答案必须写“关键路径为 A-B-D-G，总工期为 X 天”。</td></tr>
      <tr><td>总时差和自由时差混淆</td><td>总时差不影响总工期；自由时差不影响紧后活动最早开始。</td></tr>
      <tr><td>决策树忘扣初始投资</td><td>先算各概率收益，再减去投资/成本。</td></tr>
      <tr><td>合同题把买方分担和卖方分担写反</td><td>看题目比例顺序，明确“买方:卖方”还是“卖方:买方”。</td></tr>
    </tbody>
  </table>

  <h2 id="ce-sources">九、依据说明</h2>
  <div class="ce-note">
    <p>本扩展章基于近年公开案例真题解析和题型汇总进行归纳，重点参考信管网/软题库历年案例练习、希赛案例真题页面、2024-2025 考后回忆解析、以及近年计算画图题汇总页面。最新年份若为考友回忆版，仅用于判断高频趋势，不作为官方逐字题面。</p>
    <p>已交叉确认的高频计算方向包括：挣值管理、关键路径/网络图、总时差/自由时差、决策树、沟通渠道、三点估算、合同激励计算等。</p>
  </div>
</section>
"""


def main() -> None:
    source = SRC.read_text(encoding="utf-8", errors="replace")
    marker = "</body>"
    if marker not in source:
        raise SystemExit("No </body> marker found")
    output = source.replace(marker, expanded_css + "\n" + expanded_body + "\n" + marker, 1)
    OUT.write_text(output, encoding="utf-8")
    print(OUT.resolve())
    print("bytes", OUT.stat().st_size)


if __name__ == "__main__":
    main()
