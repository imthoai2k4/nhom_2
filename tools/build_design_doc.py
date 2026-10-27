from pathlib import Path
from datetime import date
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Tài_liệu_phân_tích_thiết_kế_hệ_thống_Đề_tài_48.docx"
ASSET = ROOT / ".doc_assets"
ASSET.mkdir(exist_ok=True)

NAVY = "17365D"; BLUE = "2E74B5"; PALE = "EAF2F8"; LIGHT = "F4F6F9"; GRAY = "5B6573"; GREEN = "2E7D32"; ORANGE = "B75D00"; RED = "A83232"
FONT = "Arial"
FONTPATH = "C:/Windows/Fonts/arial.ttf"
FONTBOLD = "C:/Windows/Fonts/arialbd.ttf"

def font(size, bold=False):
    return ImageFont.truetype(FONTBOLD if bold else FONTPATH, size)

def draw_diagram(name, title, nodes, edges, size=(1600, 900)):
    """Draw simple, portable UML-style diagrams from positioned boxes and labelled arrows."""
    im = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((18, 14, size[0]-18, size[1]-14), radius=20, fill="#FFFFFF", outline="#C9D9EA", width=3)
    d.text((48, 35), title, fill="#17365D", font=font(32, True))
    for x, y, w, h, label, color in nodes:
        d.rounded_rectangle((x,y,x+w,y+h), radius=18, fill=color, outline="#315C85", width=3)
        lines = label.split("\n")
        yy = y + 18
        for i, line in enumerate(lines):
            f = font(24 if i == 0 else 20, i == 0)
            bb = d.textbbox((0,0), line, font=f)
            d.text((x+(w-(bb[2]-bb[0]))/2, yy), line, fill="#132A43", font=f)
            yy += 34 if i == 0 else 29
    for edge in edges:
        x1,y1,x2,y2,*rest = edge
        label = rest[0] if rest else ""
        dash = len(rest)>1 and rest[1] == "dash"
        if dash:
            steps=18
            for i in range(0,steps,2):
                a=i/steps; b=min((i+1)/steps,1)
                d.line((x1+(x2-x1)*a,y1+(y2-y1)*a,x1+(x2-x1)*b,y1+(y2-y1)*b), fill="#496A86", width=4)
        else:
            d.line((x1,y1,x2,y2), fill="#496A86", width=4)
        import math
        ang=math.atan2(y2-y1,x2-x1)
        for da in (2.65,-2.65):
            d.line((x2,y2,x2+18*math.cos(ang+da),y2+18*math.sin(ang+da)), fill="#496A86", width=4)
        if label:
            mx=(x1+x2)/2; my=(y1+y2)/2
            bb=d.textbbox((0,0),label,font=font(18))
            d.rounded_rectangle((mx-(bb[2]-bb[0])/2-8,my-14,mx+(bb[2]-bb[0])/2+8,my+14), radius=5, fill="white")
            d.text((mx-(bb[2]-bb[0])/2,my-10),label,fill="#334E68",font=font(18))
    path=ASSET / f"{name}.png"; im.save(path); return path

def node(x,y,w,h,label,color="#EAF2F8"): return (x,y,w,h,label,color)

def create_diagrams():
    paths={}
    paths['context']=draw_diagram('01_context','Sơ đồ ngữ cảnh hệ thống',[
      node(80,290,250,120,'Quản lý\n(admin)','#DCEEFF'),node(80,530,250,120,'Người dùng / Hộ\n(user)','#E9F7EF'),
      node(610,320,360,180,'UtilityAI\nQuản lý điện nước\n+ phân tích AI','#FFF2CC'),node(1240,260,250,120,'Gemini API\n(KT3 - dự kiến)','#FCE4EC'),node(1240,530,250,120,'SQLite\nutility_mgmt.db','#EAEAEA')],
      [(330,350,610,400,'quản trị'),(330,590,610,475,'tra cứu'),(970,380,1240,320,'prompt / JSON','dash'),(970,470,1240,590,'đọc / ghi')])
    paths['architecture']=draw_diagram('02_architecture','Kiến trúc logic ba lớp',[
      node(80,220,330,140,'Trình duyệt\nHTML + CSS + Vanilla JS','#DCEEFF'),node(620,180,350,190,'FastAPI\nRouters + Pydantic\nAuth header','#FFF2CC'),node(620,530,350,150,'Services\nBilling + Alert','#E9F7EF'),node(1190,180,300,190,'SQLAlchemy ORM\nModels','#EAEAEA'),node(1190,530,300,150,'SQLite\n9 bảng','#EAEAEA')],
      [(410,290,620,275,'REST / JSON'),(795,370,795,530,'gọi nghiệp vụ'),(970,275,1190,275,'ORM'),(1340,370,1340,530,'SQL')])
    paths['usecase']=draw_diagram('03_use_case','Sơ đồ use case mức hệ thống',[
      node(60,200,240,100,'Quản lý','#DCEEFF'),node(60,600,240,100,'Người dùng / Hộ','#E9F7EF'),
      node(500,115,340,90,'Đăng nhập / xem hồ sơ','#FFF2CC'),node(500,250,340,90,'Quản lý hộ, đồng hồ','#FFF2CC'),node(500,385,340,90,'Nhập chỉ số, đơn giá','#FFF2CC'),node(500,520,340,90,'Tạo hóa đơn, ghi nhận TT','#FFF2CC'),node(500,655,340,90,'Tra cứu lịch sử, công nợ','#FFF2CC'),node(1080,385,350,110,'Phân tích AI\n(KT3 - dự kiến)','#FCE4EC')],
      [(300,250,500,160),(300,250,500,295),(300,250,500,430),(300,250,500,565),(300,650,500,700),(840,700,1080,440,'lịch sử','dash'),(300,650,500,160,'xác thực','dash')])
    paths['workflow']=draw_diagram('04_workflow','Luồng nghiệp vụ ghi chỉ số đến công nợ',[
      node(80,370,210,95,'Chọn hộ\n& đồng hồ','#DCEEFF'),node(350,370,210,95,'Nhập kỳ\n& chỉ số','#FFF2CC'),node(620,370,210,95,'Kiểm tra\nvalidation','#FFF2CC'),node(890,370,210,95,'Tính tiêu thụ\n+ cảnh báo','#E9F7EF'),node(1160,370,210,95,'Tạo hóa đơn\n+ chi tiết','#E9F7EF'),node(1430,370,130,95,'Thanh toán\n/ công nợ','#DCEEFF')],
      [(290,418,350,418),(560,418,620,418),(830,418,890,418),(1100,418,1160,418),(1370,418,1430,418)])
    paths['sequence_invoice']=draw_diagram('05_seq_invoice','Tuần tự: nhập chỉ số và sinh hóa đơn',[
      node(100,110,190,70,'Admin','#DCEEFF'),node(420,110,190,70,'Frontend','#DCEEFF'),node(740,110,190,70,'FastAPI','#FFF2CC'),node(1060,110,190,70,'Services','#E9F7EF'),node(1380,110,160,70,'SQLite','#EAEAEA')],
      [(195,220,515,220,'1. POST /readings'),(515,270,835,270,'2. request'),(835,320,1380,320,'3. đọc/ghi'),(835,380,1155,380,'4. check alert'),(1155,430,1380,430,'5. lưu alert?'),(195,510,515,510,'6. POST /invoices/generate'),(515,560,835,560,'7. request'),(835,610,1155,610,'8. generate items'),(1155,660,1380,660,'9. giá + readings + invoice')])
    paths['sequence_payment']=draw_diagram('06_seq_payment','Tuần tự: ghi nhận thanh toán',[
      node(100,130,220,75,'Admin','#DCEEFF'),node(500,130,220,75,'FastAPI payments','#FFF2CC'),node(900,130,240,75,'Invoice status','#E9F7EF'),node(1320,130,200,75,'SQLite','#EAEAEA')],
      [(210,300,610,300,'1. POST /payments'),(610,370,1320,370,'2. lấy hóa đơn + SUM đã trả'),(610,450,1320,450,'3. kiểm tra <= còn nợ'),(610,530,1010,530,'4. cập nhật paid/partial'),(1010,600,1320,600,'5. lưu payment + status')])
    paths['erd']=draw_diagram('07_erd','ERD rút gọn: 9 bảng dữ liệu',[
      node(55,95,260,135,'USERS\nPK id\nusername, role','#DCEEFF'),node(55,360,260,135,'HOUSEHOLDS\nPK id\nFK created_by','#FFF2CC'),node(420,360,260,135,'METERS\nPK id\nFK household_id','#E9F7EF'),node(785,95,280,135,'UTILITY_PRICES\nPK id\ntier, effective dates','#EAEAEA'),node(785,360,280,135,'READINGS\nPK id\nFK meter_id, period','#E9F7EF'),node(1160,360,280,135,'INVOICES\nPK id\nFK household_id, period','#FFF2CC'),node(1160,630,280,135,'INVOICE_ITEMS\nFK invoice_id, reading_id\nFK price_id','#FCE4EC'),node(785,630,280,135,'PAYMENTS\nPK id\nFK invoice_id','#DCEEFF'),node(420,630,260,135,'CONSUMPTION_ALERTS\nFK household_id, meter_id','#FCE4EC')],
      [(185,230,185,360,'1-n'),(315,427,420,427,'1-n'),(550,495,550,630,'1-n'),(680,427,785,427,'1-n'),(315,427,1160,427,'1-n'),(1300,495,1300,630,'1-n'),(925,230,925,630,'1-n'),(1300,495,925,630,'1-n'),(550,495,550,630,'1-n')])
    paths['state']=draw_diagram('08_invoice_state','Sơ đồ trạng thái hóa đơn',[
      node(100,380,230,100,'Chưa thanh toán\nunpaid','#FFF2CC'),node(630,380,230,100,'Thanh toán một phần\npartial','#DCEEFF'),node(1160,380,230,100,'Đã thanh toán\npaid','#E9F7EF'),node(630,650,230,85,'Không được xóa\nkhi đã có payment','#FCE4EC')],
      [(330,430,630,430,'trả > 0 và < tổng'),(860,430,1160,430,'trả đủ tổng'),(630,480,740,650,'đã phát sinh TT','dash')])
    paths['ai']=draw_diagram('09_ai_dataflow','Luồng dữ liệu AI (định hướng KT3)',[
      node(70,350,255,120,'Readings\nInvoice\nAlerts','#EAEAEA'),node(460,350,280,120,'Chuẩn hóa dữ liệu\n+ kiểm tra chất lượng','#FFF2CC'),node(875,350,280,120,'Prompt guard\nKhông tự tạo số liệu','#FCE4EC'),node(1290,190,220,110,'Gemini API\nJSON response','#DCEEFF'),node(1290,540,220,110,'UI: nhận xét\nalerts, gợi ý','#E9F7EF')],
      [(325,410,460,410),(740,410,875,410),(1155,390,1290,245,'request','dash'),(1400,300,1400,540,'response','dash')])
    paths['deployment']=draw_diagram('10_deployment','Sơ đồ triển khai MVP',[
      node(80,360,280,115,'Máy người dùng\nBrowser','#DCEEFF'),node(600,290,350,170,'Máy chủ ứng dụng\nUvicorn + FastAPI\nport 8000','#FFF2CC'),node(1190,200,280,115,'Lưu trữ cục bộ\nutility_mgmt.db','#EAEAEA'),node(1190,560,280,115,'Dịch vụ ngoài\nGemini (KT3)','#FCE4EC')],
      [(360,417,600,375,'HTTP'),(950,375,1190,255,'SQLAlchemy'),(950,417,1190,615,'HTTPS','dash')])
    return paths

def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr(); shd = OxmlElement('w:shd'); shd.set(qn('w:fill'), fill); tcPr.append(shd)
def border_bottom(p, color=NAVY):
    pPr=p._p.get_or_add_pPr(); b=OxmlElement('w:pBdr'); bot=OxmlElement('w:bottom'); bot.set(qn('w:val'),'single'); bot.set(qn('w:sz'),'12'); bot.set(qn('w:space'),'6'); bot.set(qn('w:color'),color); b.append(bot); pPr.append(b)
def set_cell_text(cell, text, bold=False, color=None, size=9):
    cell.text=''; p=cell.paragraphs[0]; p.paragraph_format.space_after=Pt(2); r=p.add_run(str(text)); r.bold=bold; r.font.name=FONT; r._element.rPr.rFonts.set(qn('w:ascii'),FONT); r._element.rPr.rFonts.set(qn('w:hAnsi'),FONT); r.font.size=Pt(size)
    if color: r.font.color.rgb=RGBColor.from_string(color)
    cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
def set_widths(table, widths):
    for row in table.rows:
        for cell,w in zip(row.cells,widths): cell.width=Inches(w)
def add_table(doc, headers, rows, widths=None, font_size=8.5):
    t=doc.add_table(rows=1, cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.style='Table Grid'
    for c,h in zip(t.rows[0].cells,headers): shade(c,NAVY); set_cell_text(c,h,True,'FFFFFF',font_size)
    for idx,row in enumerate(rows):
        cells=t.add_row().cells
        for c,val in zip(cells,row):
            if idx%2==1: shade(c,LIGHT)
            set_cell_text(c,val,False,None,font_size)
    if widths: set_widths(t,widths)
    doc.add_paragraph().paragraph_format.space_after=Pt(1)
    return t
def add_caption(doc, text):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(2); p.paragraph_format.space_after=Pt(8)
    r=p.add_run(text); r.italic=True; r.font.size=Pt(9); r.font.color.rgb=RGBColor.from_string(GRAY)
def add_bullet(doc,text,level=0):
    p=doc.add_paragraph(style='List Bullet' if level==0 else 'List Bullet 2'); p.paragraph_format.space_after=Pt(3); p.add_run(text)
def add_h(doc,text,level=1):
    p=doc.add_heading(text,level); p.paragraph_format.keep_with_next=True; return p
def add_para(doc,text,bold_lead=None):
    p=doc.add_paragraph(); p.paragraph_format.space_after=Pt(5); p.paragraph_format.line_spacing=1.1
    if bold_lead and text.startswith(bold_lead):
        r=p.add_run(bold_lead); r.bold=True; p.add_run(text[len(bold_lead):])
    else: p.add_run(text)
    return p
def add_diagram(doc, path, caption, width=6.35):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run().add_picture(str(path),width=Inches(width)); add_caption(doc,caption)

def style(doc):
    sec=doc.sections[0]; sec.top_margin=Inches(.75); sec.bottom_margin=Inches(.7); sec.left_margin=Inches(.75); sec.right_margin=Inches(.75); sec.header_distance=Inches(.35); sec.footer_distance=Inches(.35)
    normal=doc.styles['Normal']; normal.font.name=FONT; normal._element.rPr.rFonts.set(qn('w:ascii'),FONT); normal._element.rPr.rFonts.set(qn('w:hAnsi'),FONT); normal.font.size=Pt(10); normal.paragraph_format.space_after=Pt(5); normal.paragraph_format.line_spacing=1.1
    for s,sz,col in [('Title',26,NAVY),('Heading 1',17,BLUE),('Heading 2',13,NAVY),('Heading 3',11,GRAY)]:
        st=doc.styles[s]; st.font.name=FONT; st._element.rPr.rFonts.set(qn('w:ascii'),FONT); st._element.rPr.rFonts.set(qn('w:hAnsi'),FONT); st.font.size=Pt(sz); st.font.color.rgb=RGBColor.from_string(col)
    for s in ['Heading 1','Heading 2','Heading 3']:
        doc.styles[s].paragraph_format.space_before=Pt(12); doc.styles[s].paragraph_format.space_after=Pt(5)
    header=sec.header.paragraphs[0]; header.text='UTILITYAI  |  TÀI LIỆU PHÂN TÍCH & THIẾT KẾ HỆ THỐNG'; header.alignment=WD_ALIGN_PARAGRAPH.RIGHT; header.runs[0].font.size=Pt(8); header.runs[0].font.color.rgb=RGBColor.from_string(GRAY)
    footer=sec.footer.paragraphs[0]; footer.text='Đề tài 48 • FastAPI + SQLite + HTML/JavaScript'; footer.alignment=WD_ALIGN_PARAGRAPH.CENTER; footer.runs[0].font.size=Pt(8); footer.runs[0].font.color.rgb=RGBColor.from_string(GRAY)

def build():
    diagrams=create_diagrams(); doc=Document(); style(doc)
    # Cover
    for _ in range(5): doc.add_paragraph()
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=p.add_run('TÀI LIỆU PHÂN TÍCH VÀ\nTHIẾT KẾ HỆ THỐNG'); r.bold=True; r.font.size=Pt(27); r.font.color.rgb=RGBColor.from_string(NAVY)
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=p.add_run('Đề tài 48 – Hệ thống Quản lý Hóa đơn Điện nước Hộ gia đình có Tích hợp AI'); r.font.size=Pt(15); r.font.color.rgb=RGBColor.from_string(BLUE)
    doc.add_paragraph()
    add_table(doc,['Hạng mục','Thông tin'],[['Phiên bản','1.0'],['Cơ sở phân tích','de_tai_48.md, prompt.txt, mã nguồn hiện trạng'],['Phạm vi hiện thực','KT1–KT2 hoàn thành; KT3 AI/testing là định hướng'],['Công nghệ','FastAPI, SQLAlchemy, SQLite, HTML/CSS/Vanilla JavaScript'],['Ngày lập',date.today().strftime('%d/%m/%Y')]], [1.7,4.8],9)
    doc.add_page_break()
    add_h(doc,'Mục lục',1)
    for line in ['1. Tổng quan và phạm vi','2. Phân tích nghiệp vụ','3. Yêu cầu chức năng và phi chức năng','4. Kiến trúc hệ thống','5. Thiết kế dữ liệu','6. Thiết kế API và giao diện','7. Thiết kế xử lý nghiệp vụ','8. Thiết kế AI (KT3 – dự kiến)','9. Bảo mật, rủi ro và kiểm thử','10. Đánh giá hiện trạng và lộ trình']:
        p=doc.add_paragraph(style='List Number'); p.add_run(line)
    add_h(doc,'Quy ước trạng thái',2)
    add_table(doc,['Nhãn','Ý nghĩa'],[['Đã triển khai','Có trong mã nguồn hiện tại và được mô tả theo hành vi thực tế.'],['Dự kiến KT3','Có trong đề bài/prompt nhưng router AI, dịch vụ AI và test chưa xuất hiện trong mã nguồn.'],['Khuyến nghị','Đề xuất thiết kế nhằm khắc phục rủi ro hoặc hoàn thiện sản phẩm.']],[1.5,5.0])
    # Overview
    add_h(doc,'1. Tổng quan và phạm vi',1)
    add_h(doc,'1.1 Mục tiêu',2); add_para(doc,'Hệ thống quản lý tập trung hộ/phòng, đồng hồ, chỉ số tiêu thụ, đơn giá, hóa đơn và thanh toán. Mục tiêu là đảm bảo dữ liệu có thể truy vết, tính tiền chính xác theo kỳ và phát hiện mức tiêu thụ tăng mạnh.');
    add_h(doc,'1.2 Phạm vi MVP',2); add_table(doc,['Trong phạm vi','Ngoài phạm vi hiện thực hiện tại'],[['Đăng nhập, phân quyền admin/user; CRUD hộ, đồng hồ, chỉ số, đơn giá; tạo hóa đơn; thanh toán; báo cáo công nợ/cảnh báo.','Tích hợp Gemini thực tế; màn hình phân tích AI; JWT; phân quyền dữ liệu đến từng hộ; bộ pytest; phân trang; thanh toán trực tuyến.']],[3.2,3.3])
    add_diagram(doc,diagrams['context'],'Hình 1. Sơ đồ ngữ cảnh và ranh giới hệ thống.')
    add_h(doc,'1.3 Giả định thiết kế',2)
    for t in ['Mỗi hộ có thể gắn nhiều đồng hồ; mỗi đồng hồ là điện hoặc nước.','Một đồng hồ có duy nhất một lần ghi trong một kỳ YYYY-MM.','Tiền lưu Integer theo đơn vị đồng; chỉ số lưu Decimal/Numeric(12,2).','Giao diện hiện dùng SPA HTML/JavaScript, không phải React như phương án ban đầu.']: add_bullet(doc,t)
    # business
    add_h(doc,'2. Phân tích nghiệp vụ',1); add_h(doc,'2.1 Tác nhân và quyền',2)
    add_table(doc,['Tác nhân','Quyền đã triển khai','Giới hạn hiện trạng'],[['Quản lý (admin)','Tạo/sửa/xóa dữ liệu; nhập chỉ số; quản lý giá; tạo hóa đơn; ghi thanh toán; xem tổng quan.','Xác thực demo bằng header; mật khẩu đang so sánh plain-text.'],['Người dùng/hộ (user)','Đăng nhập và gọi các API đọc theo dependency get_current_user.','Chưa lọc dữ liệu theo hộ sở hữu; có thể thấy danh sách chung nếu biết API.'],['Gemini API (KT3)','Nhận dữ liệu tổng hợp và trả nhận xét JSON.','Chưa được include router hay cài đặt service.']],[1.2,3.0,2.3])
    add_diagram(doc,diagrams['usecase'],'Hình 2. Use case theo vai trò và trạng thái triển khai.')
    add_h(doc,'2.2 Luồng nghiệp vụ cốt lõi',2); add_diagram(doc,diagrams['workflow'],'Hình 3. Quy trình từ ghi chỉ số đến theo dõi công nợ.')
    add_h(doc,'2.3 Quy tắc nghiệp vụ',2)
    add_table(doc,['Mã','Quy tắc','Cơ chế hiện có'],[['BR-01','Kỳ có dạng YYYY-MM.','Pydantic regex.'],['BR-02','Chỉ số không âm và chỉ số mới không nhỏ hơn chỉ số cũ.','Pydantic + CHECK DB.'],['BR-03','Một meter chỉ có một reading/kỳ; một hộ chỉ có một invoice/kỳ.','Unique constraint + kiểm tra 409.'],['BR-04','Tiêu thụ = curr_reading − prev_reading.','Tính trong router readings.'],['BR-05','Thanh toán không vượt số tiền còn nợ.','Kiểm tra trước khi insert payment.'],['BR-06','Hóa đơn đã có thanh toán không thể xóa.','Trả 409.'],['BR-07','Spike khi tăng >50% so với trung bình tối đa 3 kỳ trước.','alert_service.py.']],[.7,3.5,2.3],8.4)
    # Requirements
    add_h(doc,'3. Yêu cầu chức năng và phi chức năng',1)
    add_table(doc,['Nhóm','Yêu cầu','Trạng thái'],[['Xác thực','Đăng nhập, đăng xuất, xem người dùng hiện tại.','Đã triển khai'],['Dữ liệu gốc','CRUD hộ/phòng, đồng hồ, đơn giá, chỉ số.','Đã triển khai'],['Hóa đơn','Tạo từ readings và đơn giá có hiệu lực; lưu chi tiết giá snapshot.','Đã triển khai'],['Thanh toán','Ghi nhận, tự cập nhật trạng thái, báo cáo công nợ.','Đã triển khai'],['Cảnh báo','Ghi alert spike >50% khi nhập reading.','Đã triển khai'],['AI','Tóm tắt, cảnh báo và gợi ý theo JSON.','Dự kiến KT3'],['Kiểm thử','Validation, billing, alert, AI.','Dự kiến KT3']],[1.1,4.1,1.3])
    add_h(doc,'3.1 Yêu cầu phi chức năng',2)
    for t in ['Chính xác: không dùng float cho tiền; dùng Integer và Decimal/Numeric.','Toàn vẹn: khóa ngoại, unique constraint, check constraint và transaction SQLAlchemy.','Khả năng truy vết: created_at/updated_at và các trường recorded_by/created_by tại dữ liệu chính.','Tương thích: SQLite phù hợp MVP; mô hình ORM có thể chuyển PostgreSQL.','Bảo mật: CORS hiện mở tất cả origin và auth header chỉ phù hợp demo, không phù hợp production.']: add_bullet(doc,t)
    # arch
    add_h(doc,'4. Kiến trúc hệ thống',1); add_diagram(doc,diagrams['architecture'],'Hình 4. Phân lớp frontend, FastAPI, services, ORM và SQLite.')
    add_h(doc,'4.1 Thành phần',2)
    add_table(doc,['Lớp','Thành phần','Trách nhiệm'],[['Presentation','static/index.html, css, js/app.js, js/pages/*','SPA hash routing, biểu mẫu, bảng, gọi REST.'],['API','main.py; app/routers/*','Endpoint, dependency xác thực, HTTP status, truy vấn/điều phối.'],['Domain service','billing.py; alert_service.py','Tính bậc thang/VAT, dò spike.'],['Data','models.py; database.py; SQLite','ORM, constraint, session, lưu trữ.'],['AI (future)','ai_service.py; ai_analysis.py','Chuẩn hóa dữ liệu, prompt, gọi Gemini, parse/validate JSON.']],[1.2,2.6,2.7])
    add_h(doc,'4.2 Triển khai',2); add_diagram(doc,diagrams['deployment'],'Hình 5. Sơ đồ triển khai MVP, với dịch vụ AI là tích hợp tương lai.')
    # Data
    add_h(doc,'5. Thiết kế dữ liệu',1); add_diagram(doc,diagrams['erd'],'Hình 6. ERD rút gọn của 9 bảng hiện có.')
    add_h(doc,'5.1 Bảng và quan hệ',2)
    add_table(doc,['Bảng','Mục đích','Khóa/ràng buộc chính'],[['users','Tài khoản và vai trò.','PK id; UNIQUE username.'],['households','Hộ/phòng.','FK created_by → users.'],['meters','Đồng hồ điện/nước.','FK household_id; UNIQUE meter_number.'],['utility_prices','Bậc giá và hiệu lực.','UNIQUE(meter_type,tier,effective_from); giá >0.'],['readings','Chỉ số theo kỳ.','UNIQUE(meter_id,period); curr>=prev; consumption>=0.'],['invoices','Hóa đơn theo hộ/kỳ.','UNIQUE(household_id,period).'],['invoice_items','Dòng chi tiết và snapshot giá.','FK invoice, reading, price.'],['payments','Lần thanh toán.','FK invoice; amount_paid >0.'],['consumption_alerts','Bất thường tiêu thụ.','FK household, meter; is_resolved.']],[1.4,2.4,2.7],8.2)
    add_h(doc,'5.2 Từ điển dữ liệu trọng yếu',2)
    add_table(doc,['Thực thể','Thuộc tính quan trọng','Diễn giải'],[['Reading','prev_reading, curr_reading, consumption, period','Chỉ số đầu/cuối và chênh lệch của một meter trong tháng.'],['UtilityPrice','tier, min_unit, max_unit, price_per_unit, hiệu lực','Bậc điện hoặc đơn giá nước, có lưu lịch sử.'],['Invoice','electricity_amount, water_amount, total_amount, status','Tổng tiền theo hộ/kỳ; trạng thái unpaid/partial/paid.'],['InvoiceItem','consumption, unit_price, subtotal, VAT, total','Chi tiết bill, giữ giá áp dụng khi tạo.'],['Payment','amount_paid, method, paid_at','Khoản thu để tính còn nợ.'],['ConsumptionAlert','current_consumption, avg_consumption, percent_change','Bằng chứng cảnh báo spike.']],[1.2,2.8,2.5],8.4)
    # APIs UI
    add_h(doc,'6. Thiết kế API và giao diện',1); add_h(doc,'6.1 Danh mục REST API',2)
    add_table(doc,['Nhóm','Endpoint chính','Quyền'],[['Auth','POST /api/auth/login; POST /logout; GET /me','Public / authenticated'],['Hộ','GET/POST /api/households; GET/PUT/DELETE /{id}','Đọc: authenticated; ghi: admin'],['Đồng hồ','GET/POST /api/meters; GET/PUT/DELETE /{id}','Đọc: authenticated; ghi: admin'],['Chỉ số','GET /api/readings; GET /last/{id}; GET /history/{household}; POST; PUT /{id}','Đọc: authenticated; ghi: admin'],['Đơn giá','GET/POST /api/prices; PUT /{id}','Đọc: authenticated; ghi: admin'],['Hóa đơn','GET /api/invoices; POST /generate, /generate-all; PUT status; DELETE','Đọc: authenticated; ghi: admin'],['Thanh toán/Báo cáo','GET/POST /api/payments; GET debt/summary/alerts; PUT alert resolve','Đọc: authenticated; ghi: admin cho summary/resolve']],[1.2,4.3,1.1],7.8)
    add_h(doc,'6.2 Màn hình SPA',2)
    add_table(doc,['Màn hình','Chức năng'],[['Dashboard','Trạng thái service, số hộ/đồng hồ/hóa đơn, truy cập nhanh, roadmap.'],['Đăng nhập','Nhập username/password; lưu credential hiện ở localStorage.'],['Hộ/Phòng','Danh sách, modal thêm/sửa/xóa, lọc theo trạng thái.'],['Đồng hồ','Lọc theo hộ/loại; CRUD meter.'],['Chỉ số','Chọn hộ/meter, lấy reading gần nhất, preview consumption, danh sách lịch sử.'],['Đơn giá','Bậc giá điện, nước và ngày hiệu lực.'],['Hóa đơn','Tạo một/tất cả hóa đơn, lọc và xem chi tiết.'],['Thanh toán','Nhập payment, xem công nợ.'],['Phân tích AI','Đang là trang Coming Soon KT3.']],[1.6,5.0])
    # Sequence
    add_h(doc,'7. Thiết kế xử lý nghiệp vụ',1); add_h(doc,'7.1 Nhập chỉ số và tạo hóa đơn',2); add_diagram(doc,diagrams['sequence_invoice'],'Hình 7. Trình tự xử lý chỉ số, cảnh báo và sinh hóa đơn.')
    add_h(doc,'7.2 Công thức và làm tròn',2)
    add_table(doc,['Hạng mục','Công thức/chính sách'],[['Tiêu thụ','consumption = curr_reading − prev_reading.'],['Điện','Tách consumption theo bậc đang hiệu lực, subtotal = dùng bậc × price_per_unit.'],['Nước','subtotal = consumption × đơn giá nước đang hiệu lực.'],['VAT','10% trên subtotal từng invoice item; ROUND_HALF_UP đến đồng.'],['Hóa đơn','total_amount = electricity_amount + water_amount.'],['Công nợ','outstanding_debt = total invoiced − total paid.']],[1.5,5.1])
    add_h(doc,'7.3 Thanh toán và trạng thái',2); add_diagram(doc,diagrams['sequence_payment'],'Hình 8. Trình tự ghi nhận thanh toán và cập nhật trạng thái.'); add_diagram(doc,diagrams['state'],'Hình 9. Chuyển trạng thái invoice.')
    add_h(doc,'7.4 Cảnh báo',2); add_para(doc,'Sau khi lưu reading, hệ thống lấy tối đa ba kỳ trước cùng meter. Nếu đã có dữ liệu, trung bình khác 0 và phần trăm tăng vượt 50%, service tạo ConsumptionAlert. Hiện logic không chặn bản ghi vì validation đã chặn chỉ số âm/giảm.');
    # AI
    add_h(doc,'8. Thiết kế AI (KT3 – dự kiến)',1); add_diagram(doc,diagrams['ai'],'Hình 10. Dòng dữ liệu đề xuất cho tính năng AI.')
    add_h(doc,'8.1 Hợp đồng đầu vào/đầu ra',2)
    add_table(doc,['Thành phần','Thiết kế đề xuất'],[['Input','Household, readings lịch sử, hóa đơn, alerts và ngưỡng cảnh báo; chỉ lấy từ SQLite.'],['Prompt guard','Nêu rõ không tự tạo số liệu; thiếu/mâu thuẫn phải báo data_quality_issues.'],['Output','JSON gồm summary, electricity_analysis, water_analysis, alerts[], saving_suggestions[], data_quality_issues[].'],['Validation output','Parse JSON; kiểm schema; nếu lỗi thì không hiển thị suy luận tự do, trả lỗi có thể hành động.'],['Lưu vết','Khuyến nghị lưu request fingerprint, model, prompt version, response, timestamp và reviewer action.']],[1.4,5.2])
    add_h(doc,'8.2 API đề xuất',2); add_table(doc,['Method','URL','Hành vi'],[['POST','/api/ai/analyze/{household_id}','Chuẩn hóa dữ liệu, gọi model, validate JSON, trả phân tích.'],['GET','/api/ai/history/{household_id}','Trả lịch sử kết quả đã lưu (nếu bổ sung bảng analysis_runs).']],[1.0,2.8,2.8])
    # Security QA
    add_h(doc,'9. Bảo mật, rủi ro và kiểm thử',1); add_h(doc,'9.1 Rủi ro và kiểm soát',2)
    add_table(doc,['Rủi ro','Hiện trạng','Khuyến nghị ưu tiên'],[['Lộ mật khẩu','Mật khẩu plain-text, lưu password trong localStorage và header mỗi request.','Dùng password hashing (bcrypt/argon2), JWT/httpOnly cookie, tuyệt đối không lưu mật khẩu phía client.'],['Phân quyền hộ','API đọc chưa kiểm ownership household.','Thêm user_household hoặc owner_user_id; lọc query theo user.'],['CORS','allow_origins=["*"].','Whitelist domain frontend.'],['Toàn vẹn giá','Có thể tạo các khoảng bậc chồng lấp; billing không báo thiếu giá.','Validate range/hiệu lực; từ chối invoice nếu coverage thiếu.'],['Tính nhất quán invoice','PUT status cho phép đặt tay trái với tổng payment.','Chỉ derive status từ payment; hạn chế endpoint đặt trạng thái.'],['AI ảo giác','Tính năng chưa triển khai.','Schema, guard prompt, evidence per alert, human review, log.']],[1.15,2.35,2.95],7.7)
    add_h(doc,'9.2 Ma trận kiểm thử KT3 đề xuất',2)
    add_table(doc,['ID','Tình huống','Kết quả mong đợi'],[['TC-R01','curr_reading âm','422; không lưu.'],['TC-R02','curr_reading < prev_reading','422; không lưu.'],['TC-R03','Trùng meter + period','409; không tạo reading thứ hai.'],['TC-B01','78 kWh qua 2 bậc','Tổng dòng và VAT khớp ROUND_HALF_UP.'],['TC-P01','Thanh toán vượt còn nợ','400; không lưu payment.'],['TC-A01','Tăng >50% so với lịch sử','Tạo spike alert với evidence đúng.'],['TC-AI01','Thiếu lịch sử','AI nêu không đủ dữ liệu; không tự tạo số liệu.'],['TC-AI02','Response không đúng JSON/schema','API trả lỗi kiểm soát, không render raw output.']],[.8,2.7,2.95])
    # Roadmap
    add_h(doc,'10. Đánh giá hiện trạng và lộ trình',1)
    add_table(doc,['Giai đoạn','Đánh giá','Việc còn lại'],[['KT1','Hoàn thành: mô hình 9 bảng, constraints, seed, tài liệu nền.','Cập nhật tài liệu nếu thay đổi schema.'],['KT2','Hoàn thành: CRUD FastAPI, billing, alerts, SPA pages.','Bổ sung endpoint báo cáo revenue như blueprint hoặc điều chỉnh blueprint cho khớp.'],['KT3','Chưa có mã nguồn AI router/service/test.','Tích hợp Gemini, schema output, UI AI, pytest, test API và data-quality cases.'],['Production hardening','Chưa phù hợp do demo auth/CORS và SQLite local.','JWT/hash password, ownership, migration, audit, logging, backup, PostgreSQL.']],[1.1,2.8,2.55])
    add_h(doc,'Kết luận',2); add_para(doc,'Kiến trúc hiện tại đã hình thành chuỗi nghiệp vụ cốt lõi từ dữ liệu đo đến công nợ với các ràng buộc dữ liệu quan trọng. Để đáp ứng đầy đủ tên đề tài “có tích hợp AI”, giai đoạn KT3 cần được triển khai với guard dữ liệu, schema JSON, kiểm thử tự động và các kiểm soát bảo mật trước khi đưa vào vận hành thực tế.')
    doc.save(OUT)
    print('Document created successfully')

if __name__ == '__main__': build()
