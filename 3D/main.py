import open3d as o3d
import numpy as np

# -------------- НАСТРОЙКИ ----------------
PLY_PATH = "Intergalactic_Spaceship-(Ply).ply"
VOXEL_SIZE = 0.05   # можно увеличить, если будет слишком много вокселей
POISSON_DEPTH = 6   # достаточно для задания
# -----------------------------------------


def step1_load_and_show_mesh(path: str) -> o3d.geometry.TriangleMesh:
    """1. Загрузка и визуализация (mesh)"""
    mesh = o3d.io.read_triangle_mesh(path)
    if not mesh.has_vertex_normals():
        mesh.compute_vertex_normals()

    print("STEP 1: ORIGINAL MESH")
    print("  vertices:", len(mesh.vertices))
    print("  triangles:", len(mesh.triangles))
    print("  has vertex colors:", mesh.has_vertex_colors())
    print("  has vertex normals:", mesh.has_vertex_normals())

    o3d.visualization.draw_geometries([mesh], window_name="1. Original Mesh")
    return mesh


def step2_read_point_cloud(path: str) -> o3d.geometry.PointCloud:
    """2. Преобразование в облако точек (строго через read_point_cloud)"""
    pcd = o3d.io.read_point_cloud(path)

    print("\nSTEP 2: POINT CLOUD (from PLY)")
    print("  points:", len(pcd.points))
    print("  has colors:", pcd.has_colors())

    o3d.visualization.draw_geometries([pcd], window_name="2. Point Cloud")
    return pcd


def step3_poisson_from_pcd(pcd: o3d.geometry.PointCloud) -> o3d.geometry.TriangleMesh:
    """3. Реконструкция поверхности из облака + crop"""
    mesh_rec, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=POISSON_DEPTH
    )

    # обрежем по bbox исходного облака
    bbox = pcd.get_axis_aligned_bounding_box()
    bbox = bbox.scale(1.02, bbox.get_center())
    mesh_rec = mesh_rec.crop(bbox)
    mesh_rec.compute_vertex_normals()

    print("\nSTEP 3: RECONSTRUCTED MESH (Poisson)")
    print("  vertices:", len(mesh_rec.vertices))
    print("  triangles:", len(mesh_rec.triangles))
    print("  has vertex colors:", mesh_rec.has_vertex_colors())

    o3d.visualization.draw_geometries(
        [mesh_rec], window_name="3. Reconstructed Mesh (Poisson)"
    )
    return mesh_rec


def step4_voxel_from_pcd(pcd: o3d.geometry.PointCloud, voxel_size: float) -> o3d.geometry.VoxelGrid:
    """4. Вокселизация именно point cloud (как в критериях)"""
    voxel_grid = o3d.geometry.VoxelGrid.create_from_point_cloud(pcd, voxel_size)

    print("\nSTEP 4: VOXELIZATION (from point cloud)")
    print("  voxel size:", voxel_size)
    print("  num voxels:", len(voxel_grid.get_voxels()))
    # у вокселей нет 'вершин' и 'нормалей' в том же смысле — это нормально

    o3d.visualization.draw_geometries([voxel_grid], window_name="4. Voxelized Model")
    return voxel_grid


def step5_add_plane(mesh_like) -> o3d.geometry.TriangleMesh:
    """5. Добавление плоскости рядом с объектом"""
    plane = o3d.geometry.TriangleMesh.create_box(width=2.0, height=0.01, depth=2.0)
    plane.paint_uniform_color([0.3, 0.3, 0.3])

    center = mesh_like.get_center()
    plane.translate(center)
    plane.translate([0, -0.2, 0])

    print("\nSTEP 5: PLANE + OBJECT")
    o3d.visualization.draw_geometries([plane, mesh_like], window_name="5. Plane + Object")
    return plane


def step6_clipping_by_plane(pcd: o3d.geometry.PointCloud,
                            plane: o3d.geometry.TriangleMesh) -> o3d.geometry.PointCloud:
    """6. Обрезка по плоскости (клиппинг)"""
    plane_point = plane.get_center()
    plane_normal = np.array([0.0, 1.0, 0.0])   # вверх по Y

    pts = np.asarray(pcd.points)
    vec = pts - plane_point
    dot = vec @ plane_normal

    # оставляем точки ниже плоскости
    mask = dot < 0

    clipped = o3d.geometry.PointCloud()
    clipped.points = o3d.utility.Vector3dVector(pts[mask])

    if pcd.has_colors():
        cols = np.asarray(pcd.colors)
        clipped.colors = o3d.utility.Vector3dVector(cols[mask])

    print("\nSTEP 6: CLIPPED POINT CLOUD")
    print("  points left:", len(clipped.points))
    # по критериям:
    print("  triangles: 0  (клиппинг делали на облаке точек)")
    print("  has colors:", clipped.has_colors())
    print("  has normals:", clipped.has_normals())

    o3d.visualization.draw_geometries([clipped], window_name="6. Clipped Point Cloud")
    return clipped

def step7_color_and_extremes_with_wireframe(pcd: o3d.geometry.PointCloud):
    pts = np.asarray(pcd.points)
    z = pts[:, 2]
    z_min, z_max = z.min(), z.max()
    z_norm = (z - z_min) / (z_max - z_min + 1e-8)

    # градиент по Z
    colors = np.zeros((pts.shape[0], 3))
    colors[:, 0] = z_norm          # red
    colors[:, 2] = 1 - z_norm      # blue
    pcd.colors = o3d.utility.Vector3dVector(colors)

    # экстремальные точки
    idx_min = int(np.argmin(z))
    idx_max = int(np.argmax(z))
    p_min = pts[idx_min]
    p_max = pts[idx_max]

    # -------- wireframe-коробка вокруг min ----------
    def make_wire_box(center, size=0.2, color=[1, 0, 0]):
        # создаём обычный бокс
        box = o3d.geometry.TriangleMesh.create_box(size, size, size)
        box.translate(center - np.array([size/2, size/2, size/2]))
        # превращаем в LineSet (каркас)
        lines = [
            [0,1],[1,3],[3,2],[2,0],   # нижний квадрат
            [4,5],[5,7],[7,6],[6,4],   # верхний квадрат
            [0,4],[1,5],[2,6],[3,7]    # вертикали
        ]
        points = np.asarray(box.vertices)
        line_set = o3d.geometry.LineSet(
            points=o3d.utility.Vector3dVector(points),
            lines=o3d.utility.Vector2iVector(lines)
        )
        cols = np.tile(np.array(color), (len(lines), 1))
        line_set.colors = o3d.utility.Vector3dVector(cols)
        return line_set

    min_box = make_wire_box(p_min, size=0.25, color=[0, 0, 1])  # синий
    max_box = make_wire_box(p_max, size=0.25, color=[1, 0, 0])  # красный

    # оси координат как в примере
    axes = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.5)

    print("\nSTEP 7: COLOR + EXTREMES (wireframe)")
    print("  Z min point:", p_min)
    print("  Z max point:", p_max)

    o3d.visualization.draw_geometries(
        [pcd, min_box, max_box, axes],
        window_name="7. 3D Model with Z-Extremes and Axes"
    )


def main():
    # 1
    mesh = step1_load_and_show_mesh(PLY_PATH)
    # 2
    pcd = step2_read_point_cloud(PLY_PATH)
    # 3
    mesh_rec = step3_poisson_from_pcd(pcd)
    # 4
    _ = step4_voxel_from_pcd(pcd, VOXEL_SIZE)
    # 5
    plane = step5_add_plane(mesh_rec)   # можно и mesh использовать
    # 6
    clipped = step6_clipping_by_plane(pcd, plane)
    # 7
    step7_color_and_extremes_with_wireframe(clipped)



if __name__ == "__main__":
    main()
