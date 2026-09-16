import base64
import math
import os
import subprocess
import time
import cadquery as cq
import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas

hor_tolerance = 0.8
vert_tolerance = 0.8
chamfer_multi = 1


def cut_image(h, res, height):
    chamfer = h['h_break'] * chamfer_multi
    cut_im = (
        cq.Workplane('XY')
        .box(h['h_break'], h['h_break_len'], height, centered=(1, 1, 0))
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    chamfer_top = (
        cq.Workplane('XY')
        .box(chamfer, h['h_break_len'], chamfer)
        .rotate([0, 0, 0], [0, 1, 0], 45)
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    chamfer_bot = (
        cq.Workplane('XY')
        .box(chamfer, h['h_break_len'], chamfer)
        .rotate([0, 0, 0], [0, 1, 0], 45)
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], height])
    )
    return res - cut_im - chamfer_top - chamfer_bot


def normal_hinge(h, res, height):
    chamfer = h['h_break'] * chamfer_multi
    pin_diam = (h['h_diam'] - vert_tolerance) / 3
    x_hinge = -h['h_break'] / 2 - pin_diam / 2
    res = cut_image(h, res, height)

    hole_h_im_x = (h['h_diam'] + pin_diam) / 2 + hor_tolerance
    hole_im = (
        cq.Workplane('XY')
        .box(hole_h_im_x, h['h_thick'] + hor_tolerance * 2, height, centered=(1, 1, 0))
        .translate([-hole_h_im_x / 2 - h['h_break'] / 2, 0, 0])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    res -= hole_im

    hole_diam = pin_diam + vert_tolerance
    hinge_corn = (
        cq.Workplane('XZ')
        .box(hole_h_im_x / 2 + chamfer * math.sqrt(2), h['h_diam'], h['h_thick'], centered=(0, 0, 1))
        .translate([-h['h_break'] / 2 - pin_diam / 2, 0, height / 2 - h['h_diam'] / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    hinge_ext = (
        cq.Workplane('XZ')
        .cylinder(h['h_thick'], h['h_diam'] / 2, centered=(1, 0, 1))
        .translate([x_hinge, 0, height / 2 - h['h_diam'] / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    hinge_hole = (
        cq.Workplane('XZ')
        .cylinder(h['h_thick'], hole_diam / 2, centered=(1, 0, 1))
        .translate([x_hinge, 0, height / 2 - hole_diam / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    hinge_pin = (
        cq.Workplane('XZ')
        .cylinder(h['h_thick'] + hor_tolerance * 2, pin_diam / 2, centered=(1, 0, 1))
        .translate([x_hinge, 0, height / 2 - pin_diam / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    return res + hinge_corn + hinge_ext - hinge_hole + hinge_pin


def ball_joint(h, res, height):
    res = cut_image(h, res, height)
    hole_diam = h['h_diam'] + vert_tolerance

    hole_im1 = (
        cq.Workplane('XY')
        .sphere(hole_diam / 2)
        .translate([-h['h_break'] / 2 - hole_diam / 2, 0, height / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    hole_im2 = (
        cq.Workplane('XY')
        .sphere(hole_diam / 2)
        .translate([+h['h_break'] / 2 + hole_diam / 2, 0, height / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    if h.get('h_expose', True):
        hole_join = (
            cq.Workplane('XY')
            .box(h['h_break'] + (h['h_diam'] / 2 + hor_tolerance) * 2, h['h_diam'] / 2 + hor_tolerance, height, centered=(1, 1, 0))
            .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
            .translate([h['h_tran'][0], h['h_tran'][1], 0])
        )
    else:
        hole_join = (
            cq.Workplane('YZ')
            .cylinder(h['h_break'] + h['h_diam'], h['h_diam'] / 4 + hor_tolerance)
            .translate([0, 0, height / 2])
            .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
            .translate([h['h_tran'][0], h['h_tran'][1], 0])
        )
    res -= hole_im1 + hole_im2 + hole_join

    ball1 = (
        cq.Workplane('XY')
        .sphere(h['h_diam'] / 2)
        .translate([-h['h_break'] / 2 - hole_diam / 2, 0, height / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    ball2 = (
        cq.Workplane('XY')
        .sphere(h['h_diam'] / 2)
        .translate([+h['h_break'] / 2 + hole_diam / 2, 0, height / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    join = (
        cq.Workplane('YZ')
        .cylinder(h['h_break'] + h['h_diam'], h['h_diam'] / 4)
        .translate([0, 0, height / 2])
        .rotate([0, 0, 0], [0, 0, 1], h['h_rot'])
        .translate([h['h_tran'][0], h['h_tran'][1], 0])
    )
    return res + ball1 + ball2 + join


st.set_page_config(layout="wide")

if 'height_val' not in st.session_state:
    st.session_state['height_val'] = 8.0

with st.sidebar:
    st.title("⚙️ Настройки")
    filetype = st.selectbox("Формат файла", ["jpg", "png", "jpeg", "svg"])
    out_format = st.selectbox("Формат сохранения", ["stl", "step"])
    hinge_type = st.selectbox("Тип соединения:", ["normal", "ball"])
    uploaded_file = st.file_uploader("Загрузите файл", type=[filetype])

    st.write(f"**Толщина детали (Z):** {st.session_state['height_val']:.1f} мм")
    hb1, hb2 = st.columns(2)
    with hb1:
        if st.button("➖ Тоньше"):
            st.session_state['height_val'] = max(2.0, st.session_state['height_val'] - 1.0)
            st.rerun()
    with hb2:
        if st.button("➕ Толще"):
            st.session_state['height_val'] = min(50.0, st.session_state['height_val'] + 1.0)
            st.rerun()

if uploaded_file is not None:
    raw_path = f"file.{filetype}"
    with open(raw_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    if filetype == "png":
        subprocess.run(f"convert {raw_path} -background white -alpha remove -alpha off {raw_path}", shell=True)
    if filetype != "svg":
        subprocess.run(f"convert {raw_path} file.pnm", shell=True)
        subprocess.run("potrace -s -o file.svg file.pnm", shell=True)
    else:
        subprocess.run(f"cp {raw_path} file.svg", shell=True)

    if os.path.exists("file.dxf"):
        os.remove("file.dxf")

    with open("svg_to_dxf.scad", "w") as f:
        f.write('scale([0.4, 0.4, 1]) import(file = "file.svg", center = true);')
    subprocess.run("openscad svg_to_dxf.scad -o file.dxf", shell=True)

    base_model = cq.importers.importDXF("file.dxf").wires().toPending().extrude(st.session_state['height_val'])
    bbox = base_model.combine().objects[0].BoundingBox()

    # Масштабируем картинку под ширину холста
    raw_img = Image.open(raw_path if filetype != "svg" else "file.pnm").convert("RGBA")
    c_width = 560
    c_height = int(raw_img.height * (c_width / raw_img.width))
    bg_img = raw_img.resize((c_width, c_height))

    col_canvas, col_build = st.columns([1.2, 0.8])

    # Подготавливаем готовые линии для перетаскивания мышкой
    initial_objects = [
        {"type": "line", "left": int(c_width * 0.35), "top": int(c_height * 0.2), "width": 0, "height": int(c_height * 0.6), "stroke": "#FF0000", "strokeWidth": 6},
        {"type": "line", "left": int(c_width * 0.55), "top": int(c_height * 0.2), "width": 0, "height": int(c_height * 0.6), "stroke": "#0055FF", "strokeWidth": 6},
        {"type": "line", "left": int(c_width * 0.75), "top": int(c_height * 0.2), "width": 0, "height": int(c_height * 0.6), "stroke": "#00AA00", "strokeWidth": 6}
    ]

    with col_canvas:
        st.subheader("🖱️ Интерактивный редактор разрезов")
        st.info("💡 **Кликните на цветную линию мышкой** и перетащите её вверх, вниз, влево или вправо. Кружок по центру линии — это ось петли.")
        
        canvas_result = st_canvas(
            stroke_width=6,
            stroke_color="#FF0000",
            background_image=bg_img,
            initial_drawing={"version": "4.4.0", "objects": initial_objects},
            update_streamlit=True,
            height=c_height,
            width=c_width,
            drawing_mode="transform",  # Режим трансформации и перетаскивания существующих линий мышкой
            key="drag_canvas"
        )

    # Считывание положений линий прямо с холста
    hinges = []
    if canvas_result.json_data is not None:
        objects = canvas_result.json_data.get("objects", [])
        for obj in objects:
            if obj.get("type") == "line":
                left = obj.get("left", 0)
                top = obj.get("top", 0)
                width = obj.get("width", 0) * obj.get("scaleX", 1)
                height_box = obj.get("height", 0) * obj.get("scaleY", 1)

                # Точные координаты середины отрезка (где ставится петля)
                mid_x = left + width / 2.0
                mid_y = top + height_box / 2.0

                # Центрирование относительно точки (0, 0) модели
                cq_x = ((mid_x / c_width) - 0.5) * bbox.xlen
                cq_y = -((mid_y / c_height) - 0.5) * bbox.ylen

                # Угол наклона линии
                angle = obj.get("angle", 0)
                if width != 0 and height_box != 0:
                    angle += math.degrees(math.atan2(width, height_box))

                hinges.append({
                    "type": hinge_type,
                    "h_tran": [cq_x, cq_y],
                    "h_rot": angle,
                    "h_break": 3.0,
                    "h_break_len": max(height_box * (bbox.ylen / c_height) * 1.3, bbox.ylen * 1.5),
                    "h_diam": st.session_state['height_val'],
                    "h_thick": 5.0,
                    "h_expose": True
                })

    with col_build:
        st.subheader("Сборка детали")
        st.write(f"Обнаружено шарниров: **{len(hinges)}**")
        for i, h in enumerate(hinges):
            st.write(f"• Разрез №{i+1}: X = `{h['h_tran'][0]:.1f}` мм, Y = `{h['h_tran'][1]:.1f}` мм")

        if st.button("🚀 Собрать модель (STL/STEP)", use_container_width=True):
            with st.spinner("Вырезание шарниров и сборка 3D-модели..."):
                current_height = st.session_state['height_val']
                res = cq.importers.importDXF("file.dxf").wires().toPending().extrude(current_height)

                for h in hinges:
                    if h["type"] == "normal":
                        res = normal_hinge(h, res, current_height)
                    else:
                        res = ball_joint(h, res, current_height)

                out_file = f"result.{out_format}"
                cq.exporters.export(res, out_file)
                st.success("Модель готова!")

                with open(out_file, "rb") as f:
                    st.download_button(
                        label=f"💾 Скачать {out_format.upper()}",
                        data=f,
                        file_name=out_file,
                        mime=f"model/{out_format}",
                        use_container_width=True
                    )
else:
    st.info("👈 Загрузите файл изображения в боковой панели слева.")
