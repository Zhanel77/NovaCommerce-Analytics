import open3d as o3d
import numpy as np

# путь к твоей модели
MODEL_PATH = "Intergalactic_Spaceship-(Wavefront).obj"   


NUM_SAMPLED_POINTS = 20000    
VOXEL_SIZE = 0.25             
POISSON_DEPTH = 6             


def step1_load_mesh(path: str) -> o3d.geometry.TriangleMesh:
    mesh = o3d.io.read_triangle_mesh(path)
    if not mesh.has_vertex_normals():
        mesh.compute_vertex_normals()

    print("STEP 1: ORIGINAL MESH")
    print("  vertices:", np.asarray(mesh.vertices).shape[0])
    print("  triangles:", np.asarray(mesh.triangles).shape[0])
    print("  has vertex colors:", mesh.has_vertex_colors())
    print("  has vertex normals:", mesh.has_vertex_normals())

    o3d.visualization.draw_geometries([mesh], window_name="1. Original Mesh")
    return mesh


def step2_mesh_to_clean_point_cloud(mesh: o3d.geometry.TriangleMesh,
                                    n_points: int) -> o3d.geometry.PointCloud:
    """сэмплируем точки и обрезаем верхние 'пузырьки'"""
    pcd = mesh.sample_points_uniformly(number_of_points=n_points)
    print("\nSTEP 2: POINT CLOUD (raw)")
    print("  points:", len(pcd.points))

    # получаем bbox и обрезаем верхние ~35% по оси Y
    min_b = pcd.get_min_bound()
    max_b = pcd.get_max_bound()

    # ВАЖНО: если вдруг у тебя высота по Z, поменяй строку ниже на max_b[2] = ...
    max_b[1] = min_b[1] + (max_b[1] - min_b[1]) * 0.65

    cleaned = pcd.crop(o3d.geometry.AxisAlignedBoundingBox(min_b, max_b))

    print("  points after cleaning:", len(cleaned.points))

    o3d.visualization.draw_geometries([cleaned], window_name="2. Cleaned Point Cloud")
    return cleaned


def step3_poisson_and_crop(pcd: o3d.geometry.PointCloud) -> o3d.geometry.TriangleMesh:
    """восстановление поверхности и обрезка по bbox"""
    mesh_rec, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
        pcd, depth=POISSON_DEPTH
    )

    print("\nSTEP 3: POISSON RECONSTRUCTION (raw)")
    print("  vertices:", len(mesh_rec.vertices))
    print("  triangles:", len(mesh_rec.triangles))

    # обрезаем по bbox исходного pcd, чтобы убрать лишнее
    bbox = pcd.get_axis_aligned_bounding_box()
    bbox = bbox.scale(1.02, bbox.get_center())
    mesh_rec = mesh_rec.crop(bbox)
    mesh_rec.compute_vertex_normals()

    print("  after crop -> vertices:", len(mesh_rec.vertices))
    print("  after crop -> triangles:", len(mesh_rec.triangles))

    o3d.visualization.draw_geometries([mesh_rec], window_name="3. Reconstructed Mesh (Poisson)")
    return mesh_rec


def step4_voxelize(mesh: o3d.geometry.TriangleMesh,
                   voxel_size: float) -> o3d.geometry.VoxelGrid:
    voxel_grid = o3d.geometry.VoxelGrid.create_from_triangle_mesh(mesh, voxel_size)
    print("\nSTEP 4: VOXELIZATION")
    print("  voxel size:", voxel_size)
    print("  num voxels:", len(voxel_grid.get_voxels()))
    o3d.visualization.draw_geometries([voxel_grid], window_name="4. Voxelized Model")
    return voxel_grid


def step5_create_plane_near_mesh(mesh: o3d.geometry.TriangleMesh) -> o3d.geometry.TriangleMesh:
    plane = o3d.geometry.TriangleMesh.create_box(width=2.0, height=0.01, depth=2.0)
    plane.paint_uniform_color([0.3, 0.3, 0.3])

    center = mesh.get_center()
    plane.translate(center)
    plane.translate([0, -0.2, 0])   # чуть ниже модели, чтобы было видно

    print("\nSTEP 5: PLANE + MESH")
    o3d.visualization.draw_geometries([plane, mesh], window_name="5. Plane + Mesh")
    return plane


def step6_clip_by_plane(pcd: o3d.geometry.PointCloud,
                        plane: o3d.geometry.TriangleMesh) -> o3d.geometry.PointCloud:
    plane_point = plane.get_center()
    plane_normal = np.array([0.0, 1.0, 0.0])   # ось Y

    points = np.asarray(pcd.points)
    colors = np.asarray(pcd.colors) if pcd.has_colors() else None

    vec = points - plane_point
    dot = vec @ plane_normal

    mask = dot < 0   # оставляем точки ниже плоскости

    clipped = o3d.geometry.PointCloud()
    clipped.points = o3d.utility.Vector3dVector(points[mask])
    if colors is not None and colors.shape[0] == points.shape[0]:
        clipped.colors = o3d.utility.Vector3dVector(colors[mask])

    print("\nSTEP 6: CLIPPED POINT CLOUD")
    print("  points after clipping:", len(clipped.points))

    o3d.visualization.draw_geometries([clipped], window_name="6. Clipped Point Cloud")
    return clipped


def step7_color_and_mark_extremes(pcd: o3d.geometry.PointCloud):
    pts = np.asarray(pcd.points)
    z = pts[:, 2]
    z_min, z_max = z.min(), z.max()
    z_norm = (z - z_min) / (z_max - z_min + 1e-8)

    colors = np.zeros((pts.shape[0], 3))
    colors[:, 0] = z_norm
    colors[:, 2] = 1 - z_norm
    pcd.colors = o3d.utility.Vector3dVector(colors)

    idx_min = int(np.argmin(z))
    idx_max = int(np.argmax(z))
    p_min = pts[idx_min]
    p_max = pts[idx_max]

    min_box = o3d.geometry.TriangleMesh.create_box(0.05, 0.05, 0.05)
    min_box.translate(p_min)
    min_box.paint_uniform_color([0, 1, 0])

    max_box = o3d.geometry.TriangleMesh.create_box(0.05, 0.05, 0.05)
    max_box.translate(p_max)
    max_box.paint_uniform_color([1, 0, 0])

    print("\nSTEP 7: COLOR + EXTREMES")
    print("  Z min point:", p_min)
    print("  Z max point:", p_max)

    o3d.visualization.draw_geometries(
        [pcd, min_box, max_box],
        window_name="7. Colored by Z + Extremes"
    )


def main():
    mesh = step1_load_mesh(MODEL_PATH)
    pcd = step2_mesh_to_clean_point_cloud(mesh, NUM_SAMPLED_POINTS)
    mesh_rec = step3_poisson_and_crop(pcd)
    _ = step4_voxelize(mesh_rec, VOXEL_SIZE)
    plane = step5_create_plane_near_mesh(mesh_rec)
    clipped_pcd = step6_clip_by_plane(pcd, plane)
    step7_color_and_mark_extremes(clipped_pcd)


if __name__ == "__main__":
    main()
