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
if 'hinge_list' not in st.session_state:
    st.session_state['hinge_list'] = [
        {'x': -25.0, 'y': 0.0, 'rot': 0.0, 'type': 'normal'},
        {'x': 0.0, 'y': 0.0, 'rot': 0.0, 'type': 'normal'},
        {'x': 25.0, 'y': 0.0, 'rot': 0.0, 'type': 'normal'}
    ]
if 'cur_h_idx' not in st.session_state:
    st.session_state['cur_h_idx'] = 0

with st.sidebar:
    st.title("⚙️ Настройки")
    filetype = st.selectbox("Формат файла", ["jpg", "png", "jpeg", "svg"])
    out_format = st.selectbox("Формат сохранения", ["stl", "step"])
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

    # Размер холста
    raw_img = Image.open(raw_path if filetype != "svg" else "file.pnm").convert("RGBA")
    c_width = 540
    c_height = int(raw_img.height * (c_width / raw_img.width))
    bg_img = raw_img.resize((c_width, c_height))

    col_ctrl, col_canvas = st.columns([1, 1.2])

    with col_ctrl:
        st.subheader("Управление шарниром")
        h_options = [f"Шарнир №{i+1}" for i in range(len(st.session_state['hinge_list']))]
        selected = st.selectbox("Активный шарнир для позиционирования:", h_options, index=st.session_state['cur_h_idx'])
        h_idx = h_options.index(selected)
        st.session_state['cur_h_idx'] = h_idx

        cur_h = st.session_state['hinge_list'][h_idx]
        cur_h['type'] = st.selectbox("Тип соединения:", ["normal", "ball"], index=0 if cur_h['type'] == 'normal' else 1)

        st.info("👉 **Кликните мышкой прямо по коту на картинке справа** — ось шарнира моментально прыгнет в точку клика.")

        st.markdown(f"**Текущие координаты:** X = `{cur_h['x']:.1f} мм`, Y = `{cur_h['y']:.1f} мм`")

        r1, r2 = st.columns(2)
        with r1:
            if st.button("🔄 Повернуть (-15°)"):
                cur_h['rot'] -= 15.0
                st.rerun()
        with r2:
            if st.button("🔁 Повернуть (+15°)"):
                cur_h['rot'] += 15.0
                st.rerun()

        st.write("---")
        add_c, rem_c = st.columns(2)
        with add_c:
            if st.button("➕ Добавить шарнир"):
                st.session_state['hinge_list'].append({'x': 0.0, 'y': 0.0, 'rot': 0.0, 'type': 'normal'})
                st.rerun()
        with rem_c:
            if st.button("🗑️ Удалить шарнир", disabled=(len(st.session_state['hinge_list']) <= 1)):
                st.session_state['hinge_list'].pop(h_idx)
                st.session_state['cur_h_idx'] = 0
                st.rerun()

        st.write("---")
        build_btn = st.button("🚀 Собрать модель (STL/STEP)", use_container_width=True)

    with col_canvas:
        st.subheader("Интерактивная карта (кликните мышкой)")
        # Отображаем текущие линии на холсте
        initial_lines = []
        for i, h in enumerate(st.session_state['hinge_list']):
            pix_x = int(((h['x'] / bbox.xlen) + 0.5) * c_width)
            pix_y = int(((-h['y'] / bbox.ylen) + 0.5) * c_height)
            color_str = "#FF0000" if i == h_idx else "#0055FF"
            initial_lines.append({
                "type": "line",
                "x1": pix_x, "y1": max(0, pix_y - 60),
                "x2": pix_x, "y2": min(c_height, pix_y + 60),
                "stroke": color_str, "strokeWidth": 5
            })
            initial_lines.append({
                "type": "circle",
                "left": pix_x - 8, "top": pix_y - 8,
                "radius": 8, "fill": "#FFFF00" if i == h_idx else "#FFFFFF",
                "stroke": "#000000", "strokeWidth": 2
            })

        canvas_result = st_canvas(
            stroke_width=3,
            stroke_color="#FF0000",
            background_image=bg_img,
            initial_drawing={"version": "4.4.0", "objects": initial_lines},
            update_streamlit=True,
            height=c_height,
            width=c_width,
            drawing_mode="point",
            point_display_radius=0,
            key=f"canvas_click_{h_idx}"
        )

        # Считываем точку клика мыши и мгновенно перемещаем шарнир
        if canvas_result.json_data is not None:
            objs = canvas_result.json_data.get("objects", [])
            # Ищем новую поставленную точку
            new_points = [o for o in objs if o.get("type") == "circle" and "radius" not in o]
            if new_points:
                last_pt = new_points[-1]
                click_x = last_pt.get("left", 0)
                click_y = last_pt.get("top", 0)

                # Переводим точку клика в координаты CAD-модели
                cur_h['x'] = ((click_x / c_width) - 0.5) * bbox.xlen
                cur_h['y'] = -((click_y / c_height) - 0.5) * bbox.ylen
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
    st.info("👈 Загрузите файл изображения в панели слева.")
