import concurrent.futures
import logging
import re
import threading
import unicodedata
from enum import Enum
from string import Template
from typing import Dict

import numpy as np
from pdfminer.converter import PDFConverter
from pdfminer.layout import LTChar, LTFigure, LTLine, LTPage
from pdfminer.pdffont import PDFCIDFont, PDFUnicodeNotDefined
from pdfminer.pdfinterp import PDFGraphicState, PDFResourceManager
from pdfminer.utils import apply_matrix_pt, mult_matrix
from pymupdf import Font
from tenacity import retry, wait_fixed

from pdf2zh.translator import (
    AnythingLLMTranslator,
    ArgosTranslator,
    AzureOpenAITranslator,
    AzureTranslator,
    BaseTranslator,
    BingTranslator,
    DeepLTranslator,
    DeepLXTranslator,
    DeepseekTranslator,
    DifyTranslator,
    GeminiTranslator,
    GoogleTranslator,
    GrokTranslator,
    GroqTranslator,
    MiniMaxTranslator,
    ModelScopeTranslator,
    OllamaTranslator,
    OpenAIlikedTranslator,
    OpenAITranslator,
    QwenMtTranslator,
    SiliconTranslator,
    TencentTranslator,
    XinferenceTranslator,
    ZhipuTranslator,
    X302AITranslator,
    MarianTranslator,
)

log = logging.getLogger(__name__)


class PDFConverterEx(PDFConverter):
    def __init__(
        self,
        rsrcmgr: PDFResourceManager,
    ) -> None:
        PDFConverter.__init__(self, rsrcmgr, None, "utf-8", 1, None)

    def begin_page(self, page, ctm) -> None:
        # 重载替换 cropbox
        x0, y0, x1, y1 = page.cropbox
        x0, y0 = apply_matrix_pt(ctm, (x0, y0))
        x1, y1 = apply_matrix_pt(ctm, (x1, y1))
        mediabox = (0, 0, abs(x0 - x1), abs(y0 - y1))
        self.cur_item = LTPage(page.pageno, mediabox)

    def end_page(self, page):
        # 重载返回指令流
        return self.receive_layout(self.cur_item)

    def begin_figure(self, name, bbox, matrix) -> None:
        # 重载设置 pageid
        self._stack.append(self.cur_item)
        self.cur_item = LTFigure(name, bbox, mult_matrix(matrix, self.ctm))
        self.cur_item.pageid = self._stack[-1].pageid

    def end_figure(self, _: str) -> None:
        # 重载返回指令流
        fig = self.cur_item
        assert isinstance(self.cur_item, LTFigure), str(type(self.cur_item))
        self.cur_item = self._stack.pop()
        self.cur_item.add(fig)
        return self.receive_layout(fig)

    def render_char(
        self,
        matrix,
        font,
        fontsize: float,
        scaling: float,
        rise: float,
        cid: int,
        ncs,
        graphicstate: PDFGraphicState,
    ) -> float:
        # 重载设置 cid 和 font
        try:
            text = font.to_unichr(cid)
            assert isinstance(text, str), str(type(text))
        except PDFUnicodeNotDefined:
            text = self.handle_undefined_char(font, cid)
        textwidth = font.char_width(cid)
        textdisp = font.char_disp(cid)
        item = LTChar(
            matrix,
            font,
            fontsize,
            scaling,
            rise,
            text,
            textwidth,
            textdisp,
            ncs,
            graphicstate,
        )
        self.cur_item.add(item)
        item.cid = cid  # hack 插入原字符编码
        item.font = font  # hack 插入原字符字体
        return item.adv


class Paragraph:
    def __init__(self, y, x, x0, x1, y0, y1, size, brk):
        self.y: float = y  # 初始纵坐标
        self.x: float = x  # 初始横坐标
        self.x0: float = x0  # 左边界
        self.x1: float = x1  # 右边界
        self.y0: float = y0  # 上边界
        self.y1: float = y1  # 下边界
        self.size: float = size  # 字体大小
        self.brk: bool = brk  # 换行标记
        self.line_breaks: int = 0
        self.line_end_xs: list[float] = []
        self.is_justified: bool = False


# fmt: off
class TranslateConverter(PDFConverterEx):
    def __init__(
        self,
        rsrcmgr,
        vfont: str = None,
        vchar: str = None,
        thread: int = 0,
        layout={},
        lang_in: str = "",
        lang_out: str = "",
        service: str = "",
        noto_name: str = "",
        noto: Font = None,
        envs: Dict = None,
        prompt: Template = None,
        ignore_cache: bool = False,
        callback=None,
    ) -> None:
        super().__init__(rsrcmgr)
        self.vfont = vfont
        self.vchar = vchar
        self.thread = thread if (thread and thread > 0) else 4
        self.layout = layout
        self.noto_name = noto_name
        self.noto = noto
        self.callback = callback
        self.translator: BaseTranslator = None
        self.pages_data: list = []
        # e.g. "ollama:gemma2:9b" -> ["ollama", "gemma2:9b"]
        param = service.split(":", 1)
        service_name = param[0]
        service_model = param[1] if len(param) > 1 else None
        if not envs:
            envs = {}
        for translator in [GoogleTranslator, BingTranslator, DeepLTranslator, DeepLXTranslator, OllamaTranslator, XinferenceTranslator, AzureOpenAITranslator,
                           OpenAITranslator, ZhipuTranslator, ModelScopeTranslator, SiliconTranslator, GeminiTranslator, AzureTranslator, TencentTranslator, DifyTranslator, AnythingLLMTranslator, ArgosTranslator, GrokTranslator, GroqTranslator, DeepseekTranslator, MiniMaxTranslator, OpenAIlikedTranslator, QwenMtTranslator, X302AITranslator, MarianTranslator]:
            if service_name == translator.name:
                self.translator = translator(lang_in, lang_out, service_model, envs=envs, prompt=prompt, ignore_cache=ignore_cache)
        if not self.translator:
            raise ValueError("Unsupported translation service")

    def receive_layout(self, ltpage: LTPage):
        # 段落
        sstk: list[str] = []            # 段落文字栈
        pstk: list[Paragraph] = []      # 段落属性栈
        vbkt: int = 0                   # 段落公式括号计数
        # 公式组
        vstk: list[LTChar] = []         # 公式符号组
        vlstk: list[LTLine] = []        # 公式线条组
        vfix: float = 0                 # 公式纵向偏移
        # 公式组栈
        var: list[list[LTChar]] = []    # 公式符号组栈
        varl: list[list[LTLine]] = []   # 公式线条组栈
        varf: list[float] = []          # 公式纵向偏移栈
        vlen: list[float] = []          # 公式宽度栈
        # 全局
        lstk: list[LTLine] = []         # 全局线条栈
        xt: LTChar = None               # 上一个字符
        xt_cls: int = -1                # 上一个字符所属段落，保证无论第一个字符属于哪个类别都可以触发新段落
        vmax: float = ltpage.width / 4  # 行内公式最大宽度
        ops: str = ""                   # 渲染结果

        def vflag(font: str, char: str):    # 匹配公式（和角标）字体
            if isinstance(font, bytes):     # 不一定能 decode，直接转 str
                try:
                    font = font.decode('utf-8')  # 尝试使用 UTF-8 解码
                except UnicodeDecodeError:
                    font = ""
            font = font.split("+")[-1]      # 字体名截断
            if re.match(r"\(cid:", char):
                return True
            # 基于字体名规则的判定
            if self.vfont:
                if re.match(self.vfont, font):
                    return True
            else:
                if re.match(                                            # latex 字体
                    r"(CM[^R]|MS.M|XY|MT|BL|RM|EU|LA|RS|LINE|LCIRCLE|TeX-|rsfs|txsy|wasy|stmary|.*Mono|.*Code|.*Math|.*Sym)",
                    font,
                ):
                    return True
            # 基于字符集规则的判定
            if self.vchar:
                if re.match(self.vchar, char):
                    return True
            else:
                if (
                    char
                    and char != " "                                     # 非空格
                    and (
                        unicodedata.category(char[0])
                        in ["Lm", "Mn", "Sk", "Sm", "Zl", "Zp", "Zs"]   # 文字修饰符、数学符号、分隔符号
                        or ord(char[0]) in range(0x370, 0x400)          # 希腊字母
                    )
                ):
                    return True
            return False

        # 预先扫描文档中的 URL，避免将 URL (如 https://... 或 monospace 字体) 误识别为数学公式
        url_chars = set()
        page_chars = [c for c in ltpage if isinstance(c, LTChar)]
        words = []
        curr_word = []
        for c in page_chars:
            if c.get_text().isspace():
                if curr_word:
                    words.append(curr_word)
                    curr_word = []
            else:
                curr_word.append(c)
        if curr_word:
            words.append(curr_word)
        for w in words:
            w_text = "".join(c.get_text() for c in w)
            if re.match(r"^(https?://|www\.|ftp://|[a-zA-Z0-9.-]+\.(com|org|net|edu|gov|io|ai|vn)(/|$))", w_text):
                for c in w:
                    url_chars.add(c)

        ############################################################
        # A. 原文档解析
        for child in ltpage:
            if isinstance(child, LTChar):
                cur_v = False
                layout = self.layout[ltpage.pageid]
                # ltpage.height 可能是 fig 里面的高度，这里统一用 layout.shape
                h, w = layout.shape
                # 读取当前字符在 layout 中的类别
                cx, cy = np.clip(int(child.x0), 0, w - 1), np.clip(int(child.y0), 0, h - 1)
                cls = layout[cy, cx]
                is_url_char = child in url_chars
                # 判定当前字符是否属于公式
                is_subscript = (
                    cls == xt_cls
                    and len(sstk[-1].strip()) > 1
                    and child.size < pstk[-1].size * 0.79
                    and (xt is not None and abs(child.y0 - xt.y0) > child.size * 0.15)
                )
                if not is_url_char and (                                                                    # URL 字符绝不作为数学公式处理
                    cls == 0                                                                                # 1. 类别为保留区域
                    or is_subscript                                                                         # 2. 角标字体（且存在基线偏移）
                    or vflag(child.fontname, child.get_text())                                              # 3. 公式字体
                    or (child.matrix[0] == 0 and child.matrix[3] == 0)                                      # 4. 垂直字体
                ):
                    cur_v = True
                # 判定括号组是否属于公式
                if not cur_v:
                    if vstk and child.get_text() == "(":
                        cur_v = True
                        vbkt += 1
                    if vbkt and child.get_text() == ")":
                        cur_v = True
                        vbkt -= 1
                if (                                                        # 判定当前公式是否结束
                    not cur_v                                               # 1. 当前字符不属于公式
                    or cls != xt_cls                                        # 2. 当前字符与前一个字符不属于同一段落
                    # or (abs(child.x0 - xt.x0) > vmax and cls != 0)        # 3. 段落内换行，可能是一长串斜体的段落，也可能是段内分式换行，这里设个阈值进行区分
                    # 禁止纯公式（代码）段落换行，直到文字开始再重开文字段落，保证只存在两种情况
                    # A. 纯公式（代码）段落（锚定绝对位置）sstk[-1]=="" -> sstk[-1]=="{v*}"
                    # B. 文字开头段落（排版相对位置）sstk[-1]!=""
                    or (sstk[-1] != "" and abs(child.x0 - xt.x0) > vmax)    # 因为 cls==xt_cls==0 一定有 sstk[-1]==""，所以这里不需要再判定 cls!=0
                ):
                    if vstk:
                        if (                                                # 根据公式右侧的文字修正公式的纵向偏移
                            not cur_v                                       # 1. 当前字符不属于公式
                            and cls == xt_cls                               # 2. 当前字符与前一个字符属于同一段落
                            and child.x0 > max([vch.x0 for vch in vstk])    # 3. 当前字符在公式右侧
                        ):
                            vfix = vstk[0].y0 - child.y0
                        if sstk[-1] == "":
                            xt_cls = -1 # 禁止纯公式段落（sstk[-1]=="{v*}"）的后续连接，但是要考虑新字符和后续字符的连接，所以这里修改的是上个字符的类别
                        sstk[-1] += f"{{v{len(var)}}}"
                        var.append(vstk)
                        varl.append(vlstk)
                        varf.append(vfix)
                        vstk = []
                        vlstk = []
                        vfix = 0
                # 当前字符不属于公式或当前字符是公式的第一个字符
                if not vstk:
                    is_new_para = False
                    if cls != xt_cls:
                        is_new_para = True
                    elif xt is not None and child.x1 < xt.x0:  # 换行
                        BULLET_CHARS = {"•", "▪", "▸", "►", "○", "●", "■", "◆", "◇", "·", "–", "—"}
                        line_vgap = abs(child.y0 - xt.y0)
                        char_sz = max(child.size, xt.size)
                        curr_text = sstk[-1].rstrip()
                        words = curr_text.split()
                        last_word = words[-1].lower() if words else ""

                        # 检查当前行是否为列表项 (Bullet Point)
                        is_bullet_item = child.get_text() in BULLET_CHARS

                        # 检查上一段是否为列表项，而当前行不是列表项（列表结束，正文开始）
                        was_bullet_prev = any(curr_text.lstrip().startswith(b) for b in BULLET_CHARS)
                        bullet_ended = was_bullet_prev and not is_bullet_item and (
                            child.x0 < pstk[-1].x0 - 5.0 or line_vgap >= char_sz * 1.3 or (curr_text and curr_text[-1] in ".?!:;")
                        )

                        # 检查上一行是否以介词、冠词、连词或属格 ('s) 结尾，或者当前行以小写字母开头（属于同一断句短语）
                        is_continuation = (
                            curr_text.endswith("'s")
                            or curr_text.endswith("’s")
                            or last_word in {
                                "a", "an", "the", "to", "of", "in", "for", "with", "on", "at",
                                "from", "by", "and", "or", "nor", "but", "so", "yet", "as", "into"
                            }
                            or child.get_text().islower()
                        )
                        if is_bullet_item or bullet_ended:
                            is_new_para = True
                        # 1. 明显的垂直行距 (>= 1.7 倍字号，例如目录、列表项、分段)
                        elif line_vgap >= char_sz * 1.7 and not is_continuation:
                            is_new_para = True
                        # 2. 前一行提前结束（留白较多）且垂直行距 >= 1.2 倍字号，或前一行以标点结尾
                        elif line_vgap >= char_sz * 1.2 and not is_continuation:
                            if curr_text and curr_text[-1] in ".?!:;":
                                is_new_para = True
                            elif xt.x1 < (ltpage.width - 72.0) and (xt.x1 - pstk[-1].x0 < 0.75 * (ltpage.width - 2 * 36.0)):
                                is_new_para = True

                    if not is_new_para:               # 当前字符与前一个字符属于同一段落
                        space_threshold = max(2.0, max(child.size, xt.size) * 0.22)
                        if child.x0 > xt.x1 + space_threshold:    # 添加行内空格
                            if sstk and not sstk[-1].endswith(" ") and child.get_text() != " ":
                                sstk[-1] += " "
                        elif child.x1 < xt.x0:      # 添加换行空格并标记原文段落存在换行
                            if sstk and not sstk[-1].endswith(" ") and child.get_text() != " ":
                                sstk[-1] += " "
                            pstk[-1].brk = True
                            pstk[-1].line_breaks += 1
                            pstk[-1].line_end_xs.append(xt.x1)
                    else:                           # 根据当前字符构建一个新的段落
                        sstk.append("")
                        pstk.append(Paragraph(child.y0, child.x0, child.x0, child.x0, child.y0, child.y1, child.size, False))
                if not cur_v:                                               # 文字入栈
                    ch_txt = child.get_text()
                    is_punc = ch_txt in "’'\"”‘.,:;!?-–— \t\r\n"
                    if (                                                    # 根据当前字符修正段落属性
                        (child.size > pstk[-1].size and not is_punc)        # 1. 当前字符比段落字体大且非标点符号
                        or len(sstk[-1].strip()) == 1                       # 2. 当前字符为段落第二个文字（考虑首字母放大的情况）
                    ) and ch_txt != " ":                                    # 3. 当前字符不是空格
                        pstk[-1].y -= child.size - pstk[-1].size            # 修正段落初始纵坐标，假设两个不同大小字符的上边界对齐
                        pstk[-1].size = child.size
                    sstk[-1] += ch_txt
                else:                                                       # 公式入栈
                    if (                                                    # 根据公式左侧的文字修正公式的纵向偏移
                        not vstk                                            # 1. 当前字符是公式的第一个字符
                        and cls == xt_cls                                   # 2. 当前字符与前一个字符属于同一段落
                        and child.x0 > xt.x0                                # 3. 前一个字符在公式左侧
                    ):
                        vfix = child.y0 - xt.y0
                    vstk.append(child)
                # 更新段落边界，因为段落内换行之后可能是公式开头，所以要在外边处理
                pstk[-1].x0 = min(pstk[-1].x0, child.x0)
                pstk[-1].x1 = max(pstk[-1].x1, child.x1)
                pstk[-1].y0 = min(pstk[-1].y0, child.y0)
                pstk[-1].y1 = max(pstk[-1].y1, child.y1)
                # 更新上一个字符
                xt = child
                xt_cls = cls
            elif isinstance(child, LTFigure):   # 图表
                pass
            elif isinstance(child, LTLine):     # 线条
                layout = self.layout[ltpage.pageid]
                # ltpage.height 可能是 fig 里面的高度，这里统一用 layout.shape
                h, w = layout.shape
                # 读取当前线条在 layout 中的类别
                cx, cy = np.clip(int(child.x0), 0, w - 1), np.clip(int(child.y0), 0, h - 1)
                cls = layout[cy, cx]
                if vstk and cls == xt_cls:      # 公式线条
                    vlstk.append(child)
                else:                           # 全局线条
                    lstk.append(child)
            else:
                pass
        # 处理结尾
        if vstk:    # 公式出栈
            sstk[-1] += f"{{v{len(var)}}}"
            var.append(vstk)
            varl.append(vlstk)
            varf.append(vfix)
        log.debug("\n==========[VSTACK]==========\n")
        for id, v in enumerate(var):  # 计算公式宽度
            l = max([vch.x1 for vch in v]) - v[0].x0
            log.debug(f'< {l:.1f} {v[0].x0:.1f} {v[0].y0:.1f} {v[0].cid} {v[0].fontname} {len(varl[id])} > v{id} = {"".join([ch.get_text() for ch in v])}')
            vlen.append(l)

        # Detect paragraph justification (căn đều hai bên) from original lines
        for p in pstk:
            line_w = p.x1 - p.x0
            if p.line_breaks >= 1 and line_w > 50 and len(p.line_end_xs) >= 1:
                margin_tol = max(3.0 * p.size, line_w * 0.04)
                p.is_justified = all((p.x1 - end_x) <= margin_tol for end_x in p.line_end_xs)

        ############################################################
        # B. 段落翻译
        log.debug("\n==========[SSTACK]==========\n")

        total_s = max(1, len(sstk))
        done_s = 0
        done_lock = threading.Lock()

        @retry(wait=wait_fixed(1))
        def worker(s: str):  # 多线程翻译
            nonlocal done_s
            p_idx = getattr(self, "current_page_idx", 1)
            t_pages = getattr(self, "total_pages", 1)
            if not s.strip() or re.match(r"^\{v\d+\}$", s):  # 空白和公式不翻译
                with done_lock:
                    done_s += 1
                    if self.callback:
                        self.callback({
                            "type": "translate",
                            "done": done_s,
                            "total": total_s,
                            "page": p_idx,
                            "total_pages": t_pages,
                        })
                return s
            try:
                # 保护列表项开头的 Bullet 符号（•, ▪, ▸ 等），防止翻译引擎篡改、重复或丢失
                bullet_prefix = ""
                m_bullet = re.match(r"^(\s*[•▪▸►○●■◆◇·–—]\s*)", s)
                if m_bullet:
                    bullet_prefix = m_bullet.group(1)
                    s_to_trans = s[len(bullet_prefix):]
                else:
                    s_to_trans = s

                s_clean = s_to_trans.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"').replace("\ufffd", "'")
                if re.search(r'\b[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]\b', s_clean):
                    chunks = re.split(r'(\{v\d+\}|\s{2,})', s_clean)
                    new_chunks = []
                    for chunk in chunks:
                        if chunk.startswith('{v') or (chunk.startswith(' ') and len(chunk) >= 2):
                            new_chunks.append(chunk)
                        else:
                            tokens = chunk.strip().split(' ')
                            if len(tokens) >= 2 and all(len(t) == 1 or t in ("'s", "'t", "'d", "'m", "'re", "'ve", "'ll") for t in tokens):
                                new_chunks.append("".join(tokens))
                            else:
                                new_chunks.append(chunk)
                    s_clean = re.sub(r'[ \t]{2,}', ' ', "".join(new_chunks)).strip()

                new = self.translator.translate(s_clean)
                if new:
                    new = unicodedata.normalize("NFC", new)
                if bullet_prefix:
                    new = bullet_prefix + (new or "")
                with done_lock:
                    done_s += 1
                    if self.callback:
                        self.callback({
                            "type": "translate",
                            "done": done_s,
                            "total": total_s,
                            "page": p_idx,
                            "total_pages": t_pages,
                        })
                return new
            except BaseException as e:
                if log.isEnabledFor(logging.DEBUG):
                    log.exception(e)
                else:
                    log.exception(e, exc_info=False)
                raise e
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.thread
        ) as executor:
            news = list(executor.map(worker, sstk))

        ############################################################
        # C. 新文档排版
        def raw_string(fcur: str, cstk: str):  # 编码字符串
            if fcur == self.noto_name:
                return "".join(["%04x" % self.noto.has_glyph(ord(c)) for c in cstk])
            elif isinstance(self.fontmap[fcur], PDFCIDFont):  # 判断编码长度
                return "".join(["%04x" % ord(c) for c in cstk])
            else:
                return "".join(["%02x" % ord(c) for c in cstk])

        # 根据目标语言获取默认行距
        LANG_LINEHEIGHT_MAP = {
            "zh-cn": 1.4, "zh-tw": 1.4, "zh-hans": 1.4, "zh-hant": 1.4, "zh": 1.4,
            "ja": 1.1, "ko": 1.2, "en": 1.2, "ar": 1.0, "ru": 0.8, "uk": 0.8, "ta": 0.8,
            "vi": 1.25, "vietnamese": 1.25
        }
        default_line_height = LANG_LINEHEIGHT_MAP.get(self.translator.lang_out.lower(), 1.1) # 小语种默认1.1
        _x, _y = 0, 0
        ops_list = []

        def gen_op_txt(font, size, x, y, rtxt):
            return f"/{font} {size:f} Tf 1 0 0 1 {x:f} {y:f} Tm [<{rtxt}>] TJ "

        def gen_op_line(x, y, xlen, ylen, linewidth):
            return f"ET q 1 0 0 1 {x:f} {y:f} cm [] 0 d 0 J {linewidth:f} w 0 0 m {xlen:f} {ylen:f} l S Q BT "

        def get_char_info(ch: str, size: float):
            fcur_ = None
            if self.translator.lang_out.lower() in ["vi", "vietnamese"]:
                if self.noto and self.noto.has_glyph(ord(ch)):
                    fcur_ = self.noto_name
            if fcur_ is None:
                try:
                    if self.fontmap["tiro"].to_unichr(ord(ch)) == ch:
                        fcur_ = "tiro"
                except Exception:
                    pass
            if fcur_ is None:
                fcur_ = self.noto_name
            if fcur_ == self.noto_name:
                adv = self.noto.char_lengths(ch, size)[0]
            else:
                adv = self.fontmap[fcur_].char_width(ord(ch)) * size
            return fcur_, adv

        def tokenize(text: str) -> list[str]:
            pattern = re.compile(
                r"(\{\s*v[\d\s]+\}|[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]|[\s]+|[^\s\{\}\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]+)",
                re.IGNORECASE,
            )
            return [m.group(0) for m in pattern.finditer(text) if m.group(0)]

        def layout_paragraph_tokens(tokens, p_obj, cur_size):
            p_x0 = p_obj.x0
            page_right_margin = ltpage.width - max(36.0, p_obj.x0)
            p_x1 = max(p_obj.x1, page_right_margin)
            p_brk = p_obj.brk
            
            # If paragraph starts with extreme offset (e.g. Part I), align to p_x0 to prevent asymmetric deformation
            if p_obj.x - p_obj.x0 > 2.5 * cur_size:
                cur_x = p_obj.x0
            else:
                cur_x = p_obj.x

            lidx = 0
            ops_vals = []
            fcur = None
            word_counter = 0

            def push_word_internal(w_str, t_x, l_idx, w_id, color=None):
                cur_f = None
                cur_chunk = ""
                cur_tx = t_x
                c_x = t_x
                for c in w_str:
                    f_, a_ = get_char_info(c, cur_size)
                    if cur_f is None:
                        cur_f = f_
                        cur_chunk = c
                    elif f_ != cur_f:
                        w_ = sum(get_char_info(ch, cur_size)[1] for ch in cur_chunk)
                        ops_vals.append({
                            "type": OpType.TEXT,
                            "font": cur_f,
                            "size": cur_size,
                            "x": cur_tx,
                            "dy": 0,
                            "rtxt": raw_string(cur_f, cur_chunk),
                            "lidx": l_idx,
                            "width": w_,
                            "word_id": w_id,
                            "color": color,
                        })
                        cur_chunk = c
                        cur_f = f_
                        cur_tx = c_x
                    else:
                        cur_chunk += c
                    c_x += a_
                if cur_chunk:
                    w_ = sum(get_char_info(ch, cur_size)[1] for ch in cur_chunk)
                    ops_vals.append({
                        "type": OpType.TEXT,
                        "font": cur_f,
                        "size": cur_size,
                        "x": cur_tx,
                        "dy": 0,
                        "rtxt": raw_string(cur_f, cur_chunk),
                        "lidx": l_idx,
                        "width": w_,
                        "word_id": w_id,
                        "color": color,
                    })

            for tok in tokens:
                vy_regex = re.match(r"\{\s*v([\d\s]+)\}", tok, re.IGNORECASE)
                if vy_regex:
                    try:
                        vid = int(vy_regex.group(1).replace(" ", ""))
                        adv = vlen[vid]
                    except Exception:
                        continue

                    should_wrap_v = (
                        (p_brk and cur_x + adv > p_x1 + 0.1 * cur_size)
                        or (cur_x + adv > ltpage.width - 25.0)
                    ) and (cur_x > p_x0 + 0.1 * cur_size)

                    if should_wrap_v:
                        cur_x = p_x0
                        lidx += 1

                    fix = varf[vid] if fcur is not None else 0
                    for vch in var[vid]:
                        vc = chr(vch.cid)
                        ops_vals.append({
                            "type": OpType.TEXT,
                            "font": self.fontid[vch.font],
                            "size": vch.size,
                            "x": cur_x + vch.x0 - var[vid][0].x0,
                            "dy": fix + vch.y0 - var[vid][0].y0,
                            "rtxt": raw_string(self.fontid[vch.font], vc),
                            "lidx": lidx,
                            "width": vch.width,
                        })
                    for l in varl[vid]:
                        if l.linewidth < 5:
                            ops_vals.append({
                                "type": OpType.LINE,
                                "x": l.pts[0][0] + cur_x - var[vid][0].x0,
                                "dy": l.pts[0][1] + fix - var[vid][0].y0,
                                "linewidth": l.linewidth,
                                "xlen": l.pts[1][0] - l.pts[0][0],
                                "ylen": l.pts[1][1] - l.pts[0][1],
                                "lidx": lidx,
                            })
                    cur_x += adv
                    fcur = None
                    continue

                if tok.isspace():
                    if cur_x <= p_x0 + 0.1 * cur_size:
                        continue
                    _, adv = get_char_info(" ", cur_size)
                    should_wrap_sp = (
                        (p_brk and cur_x + adv > p_x1 + 0.1 * cur_size)
                        or (cur_x + adv > ltpage.width - 25.0)
                    ) and (cur_x > p_x0 + 0.1 * cur_size)

                    if should_wrap_sp:
                        cur_x = p_x0
                        lidx += 1
                    else:
                        cur_x += adv
                    continue

                # Normal word token
                is_url_tok = bool(re.search(r"^(https?://|www\.)", tok))
                tok_color = (0.0, 0.2, 0.85) if is_url_tok else None

                char_infos = [get_char_info(c, cur_size) for c in tok]
                word_width = sum(adv for _, adv in char_infos)

                should_wrap_w = (
                    (p_brk and cur_x + word_width > p_x1 + 0.1 * cur_size)
                    or (cur_x + word_width > ltpage.width - 25.0)
                ) and (cur_x > p_x0 + 0.1 * cur_size)

                if should_wrap_w:
                    cur_x = p_x0
                    lidx += 1

                word_counter += 1
                push_word_internal(tok, cur_x, lidx, word_counter, color=tok_color)
                cur_x += word_width

            return ops_vals, lidx

        paras_layout = []
        for id, new in enumerate(news):
            p = pstk[id]
            size = p.size
            height = p.y1 - p.y0
            tokens = tokenize(new)
            orig_lines = max(1, p.line_breaks + 1)

            # 1. Format with original font size
            ops_vals, lidx = layout_paragraph_tokens(tokens, p, size)
            eff_size = size

            # 2. Smart auto-fit for single-line headings (not p.brk)
            if not p.brk and lidx > 0:
                for scale in [0.90, 0.82, 0.75]:
                    test_size = size * scale
                    test_ops, test_lidx = layout_paragraph_tokens(tokens, p, test_size)
                    if test_lidx == 0:
                        ops_vals = test_ops
                        lidx = test_lidx
                        eff_size = test_size
                        break

            # 3. Micro-scaling for multi-line paragraphs
            if p.brk and (lidx + 1) > orig_lines:
                for scale in [0.94, 0.90]:
                    test_size = size * scale
                    test_ops, test_lidx = layout_paragraph_tokens(tokens, p, test_size)
                    if (test_lidx + 1) <= orig_lines:
                        ops_vals = test_ops
                        lidx = test_lidx
                        eff_size = test_size
                        break

            # 3. Apply paragraph justification if original was justified
            if p.is_justified and ops_vals:
                max_lidx = max(v.get("lidx", 0) for v in ops_vals)
                for l in range(max_lidx):
                    line_ops = [v for v in ops_vals if v.get("lidx") == l and v.get("type") == OpType.TEXT]
                    if not line_ops:
                        continue
                    word_groups = []
                    seen_words = set()
                    for v in line_ops:
                        w_id = v.get("word_id")
                        if w_id is not None:
                            if w_id not in seen_words:
                                seen_words.add(w_id)
                                word_groups.append([v])
                            else:
                                word_groups[-1].append(v)
                        else:
                            word_groups.append([v])
                    num_gaps = len(word_groups) - 1
                    if num_gaps >= 1:
                        last_op = word_groups[-1][-1]
                        line_end_x = last_op["x"] + last_op.get("width", 0)
                        slack = p.x1 - line_end_x
                        if 0 < slack <= (p.x1 - p.x0) * 0.25:
                            gap_add = slack / num_gaps
                            for idx_w, grp in enumerate(word_groups):
                                for v in grp:
                                    v["x"] += idx_w * gap_add

            # 4. Adaptive line height
            line_height = default_line_height
            if lidx > 0 and height > 0:
                needed_lh = (height / lidx) / eff_size
                if needed_lh < line_height:
                    line_height = max(1.05, needed_lh)

            paras_layout.append({
                "id": id,
                "orig_y": p.y,
                "x0": p.x0,
                "x1": p.x1,
                "size": eff_size,
                "line_height": line_height,
                "lidx": lidx,
                "ops_vals": ops_vals,
                "rendered_height": lidx * eff_size * line_height,
            })

        # 5. Dynamic vertical collision prevention across paragraphs in the same column
        y_shifts = [0.0] * len(paras_layout)
        for i in range(len(paras_layout)):
            y_i = paras_layout[i]["orig_y"] - y_shifts[i]
            bottom_i = y_i - paras_layout[i]["rendered_height"]
            for j in range(i + 1, len(paras_layout)):
                overlap_x = min(paras_layout[i]["x1"], paras_layout[j]["x1"]) - max(paras_layout[i]["x0"], paras_layout[j]["x0"])
                is_same_col = overlap_x > 30 or abs(paras_layout[i]["x0"] - paras_layout[j]["x0"]) < 50
                if is_same_col and paras_layout[j]["orig_y"] <= paras_layout[i]["orig_y"]:
                    y_j = paras_layout[j]["orig_y"] - y_shifts[j]
                    min_gap = max(paras_layout[i]["size"], paras_layout[j]["size"]) * 1.15
                    target_max_y = bottom_i - min_gap
                    if y_j > target_max_y:
                        needed_push = y_j - target_max_y
                        y_shifts[j] += needed_push

        for idx, pl in enumerate(paras_layout):
            final_y = pl["orig_y"] - y_shifts[idx]
            for vals in pl["ops_vals"]:
                actual_y = vals["dy"] + final_y - vals["lidx"] * pl["size"] * pl["line_height"]
                if vals["type"] == OpType.TEXT:
                    if vals.get("color"):
                        r, g, b = vals["color"]
                        ops_list.append(f"q {r:.2f} {g:.2f} {b:.2f} rg /{vals['font']} {vals['size']:f} Tf 1 0 0 1 {vals['x']:f} {actual_y:f} Tm [<{vals['rtxt']}>] TJ Q ")
                    else:
                        ops_list.append(gen_op_txt(vals["font"], vals["size"], vals["x"], actual_y, vals["rtxt"]))
                elif vals["type"] == OpType.LINE:
                    ops_list.append(gen_op_line(vals["x"], actual_y, vals["xlen"], vals["ylen"], vals["linewidth"]))

        for l in lstk:  # 排版全局线条
            if l.linewidth < 5:  # hack 有的文档会用粗线条当图片背景
                ops_list.append(gen_op_line(l.pts[0][0], l.pts[0][1], l.pts[1][0] - l.pts[0][0], l.pts[1][1] - l.pts[0][0], l.linewidth))

        # Collect structured page data for DOCX export
        page_doc_paragraphs = []
        formulas_text = []
        for v_grp in var:
            f_str = "".join([vch.get_text() if hasattr(vch, "get_text") else chr(getattr(vch, "cid", 32)) for vch in v_grp])
            formulas_text.append(f_str)

        page_h = getattr(ltpage, "height", 842.0)
        for id, pl in enumerate(paras_layout):
            p_orig = pstk[id]
            t_text = news[id]
            page_doc_paragraphs.append({
                "text": t_text,
                "orig_text": sstk[id],
                "size": pl["size"],
                "is_justified": p_orig.is_justified,
                "x0": pl["x0"],
                "x1": pl["x1"],
                "y_top": page_h - getattr(p_orig, "y", 0.0),
            })

        self.pages_data.append({
            "page_id": ltpage.pageid,
            "paragraphs": page_doc_paragraphs,
            "formulas": formulas_text,
            "images": [],
        })

        ops = f"BT {''.join(ops_list)}ET "
        return ops


class OpType(Enum):
    TEXT = "text"
    LINE = "line"
