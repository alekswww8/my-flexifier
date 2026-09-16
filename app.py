import base64
import math
import os
import subprocess
import time
import cadquery as cq
import streamlit as st
from PIL import Image, ImageDraw
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
if 'hinge_list' not in st.session_state:
    st.session_state['hinge_list'] = [
        {'x': -25.0, 'y': 0.0, 'rot': 0.0, 'type': 'normal'},
        {'x': 0.0, 'y': 0.0, 'rot': 0.0, 'type': 'normal'},
        {'x': 25.0, 'y': 0.0, 'rot': 0.0, 'type': 'normal'}
    ]
if 'cur_h_idx' not in st.session_state:
    st.session_state['cur_h_idx'] = 0

# ВЕРХНЯЯ СТРОКА НАСТРОЕК
t1, t2, t3, t4 = st.columns([1, 1, 2, 1.2])
with t1:
    filetype = st.selectbox("Формат файла", ["jpg", "png", "jpeg", "svg"])
with t2:
    out_format = st.selectbox("Формат сохранения", ["stl", "step"])
with t3:
    uploaded_file = st.file_uploader("Загрузите файл", type=[filetype])
with t4:
    st.write(f"**Толщина Z:** {st.session_state['height_val']:.1f} мм")
    hb1, hb2 = st.columns(2)
    with hb1:
        if st.button("➖ 1мм"):
            st.session_state['height_val'] = max(2.0, st.session_state['height_val'] - 1.0)
            st.rerun()
    with hb2:
        if st.button("➕ 1мм"):
            st.session_state['height_val'] = min(50.0, st.session_state['height_val'] + 1.0)
            st.rerun()

st.write("---")

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

    # Широкий холст под фигуру
    raw_img = Image.open(raw_path if filetype != "svg" else "file.pnm").convert("RGBA")
    c_width = 850
    c_height = int(raw_img.height * (c_width / raw_img.width))
    bg_img = raw_img.resize((c_width, c_height))

    # Колонки: узкое управление [1] и широкая карта [3.5]
    col_ctrl, col_canvas = st.columns([1, 3.5])

    with col_ctrl:
        st.write("### 🎛️ Шарнир")
        h_options = [f"Шарнир №{i+1}" for i in range(len(st.session_state['hinge_list']))]
        selected = st.selectbox("Выбор:", h_options, index=st.session_state['cur_h_idx'])
        h_idx = h_options.index(selected)
        st.session_state['cur_h_idx'] = h_idx

        cur_h = st.session_state['hinge_list'][h_idx]
        cur_h['type'] = st.selectbox("Тип:", ["normal", "ball"], index=0 if cur_h['type'] == 'normal' else 1)

        st.caption("Кликните мышкой по телу кота справа для переноса оси.")
        st.markdown(f"`X: {cur_h['x']:.1f} | Y: {cur_h['y']:.1f} мм`")

        r1, r2 = st.columns(2)
        with r1:
            if st.button("🔄 -15°"):
                cur_h['rot'] -= 15.0
                st.rerun()
        with r2:
            if st.button("🔁 +15°"):
                cur_h['rot'] += 15.0
                st.rerun()

        ac1, ac2 = st.columns(2)
        with ac1:
            if st.button("➕ Доб."):
                st.session_state['hinge_list'].append({'x': 0.0, 'y': 0.0, 'rot': 0.0, 'type': 'normal'})
                st.rerun()
        with ac2:
            if st.button("🗑️ Удал.", disabled=(len(st.session_state['hinge_list']) <= 1)):
                st.session_state['hinge_list'].pop(h_idx)
                st.session_state['cur_h_idx'] = 0
                st.rerun()

        st.write("---")
        build_btn = st.button("🚀 Собрать STL", use_container_width=True)

    with col_canvas:
        # Наносим линии и маркеры шарниров прямо на картинку
        img_overlay = bg_img.copy()
        draw = ImageDraw.Draw(img_overlay)

        for i, h in enumerate(st.session_state['hinge_list']):
            px = int(((h['x'] / bbox.xlen) + 0.5) * c_width)
            py = int(((-h['y'] / bbox.ylen) + 0.5) * c_height)
            is_cur = (i == h_idx)

            line_color = (255, 0, 0, 255) if is_cur else (0, 85, 255, 255)
            dot_color = (255, 255, 0, 255) if is_cur else (255, 255, 255, 255)

            rad = math.radians(h['rot'])
            dx = math.sin(rad) * 70
            dy = math.cos(rad) * 70
            draw.line([(px - dx, py - dy), (px + dx, py + dy)], fill=line_color, width=6)
            draw.ellipse([(px - 10, py - 10), (px + 10, py + 10)], fill=dot_color, outline=(0, 0, 0, 255), width=2)

        canvas_result = st_canvas(
            stroke_width=0,
            background_image=img_overlay,
            update_streamlit=True,
            height=c_height,
            width=c_width,
            drawing_mode="point",
            point_display_radius=8,
            key=f"canvas_{h_idx}_{len(st.session_state['hinge_list'])}"
        )

        # Считывание клика мыши без задержек
        if canvas_result.json_data is not None:
            objs = canvas_result.json_data.get("objects", [])
            if objs:
                last_pt = objs[-1]
                click_x = last_pt.get("left", 0)
                click_y = last_pt.get("top", 0)

                new_x = ((click_x / c_width) - 0.5) * bbox.xlen
                new_y = -((click_y / c_height) - 0.5) * bbox.ylen

                if abs(new_x - cur_h['x']) > 0.5 or abs(new_y - cur_h['y']) > 0.5:
                    cur_h['x'] = new_x
                    cur_h['y'] = new_y
                    st.rerun()

    if build_btn:
        with st.spinner("Сборка 3D-модели в CadQuery..."):
            current_height = st.session_state['height_val']
            res = cq.importers.importDXF("file.dxf").wires().toPending().extrude(current_height)

            for h in st.session_state['hinge_list']:
                h_dict = {
                    "type": h["type"],
                    "h_tran": [h["x"], h["y"]],
                    "h_rot": h["rot"],
                    "h_break": 3.0,
                    "h_break_len": bbox.ylen * 2.0,
                    "h_diam": current_height,
                    "h_thick": 5.0,
                    "h_expose": True
                }
                if h["type"] == "normal":
                    res = normal_hinge(h_dict, res, current_height)
                else:
                    res = ball_joint(h_dict, res, current_height)

            out_file = f"result.{out_format}"
            cq.exporters.export(res, out_file)
            st.success("Готово!")

            with open(out_file, "rb") as f:
                st.download_button(
                    label=f"💾 Скачать {out_format.upper()}",
                    data=f,
                    file_name=out_file,
                    mime=f"model/{out_format}",
                    use_container_width=True
                )
else:
    st.info("👈 Загрузите файл изображения в блоке настроек выше, чтобы начать.")
