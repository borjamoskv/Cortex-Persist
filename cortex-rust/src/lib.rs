use pyo3::prelude::*;
use std::collections::HashSet;

#[pyfunction]
fn move_grid(grid: Vec<Vec<u8>>, dx: i32, dy: i32) -> PyResult<Vec<Vec<u8>>> {
    let rows = grid.len();
    if rows == 0 { return Ok(grid); }
    let cols = grid[0].len();
    let mut new_grid = vec![vec![0; cols]; rows];

    for r in 0..rows {
        for c in 0..cols {
            if grid[r][c] != 0 {
                let nr = r as i32 + dy;
                let nc = c as i32 + dx;
                if nr >= 0 && (nr as usize) < rows && nc >= 0 && (nc as usize) < cols {
                    new_grid[nr as usize][nc as usize] = grid[r][c];
                }
            }
        }
    }
    Ok(new_grid)
}

#[pyfunction]
fn rotate_grid(grid: Vec<Vec<u8>>, angle: i32) -> PyResult<Vec<Vec<u8>>> {
    match angle {
        90 => {
            let rows = grid.len();
            let cols = grid[0].len();
            let mut rotated = vec![vec![0; rows]; cols];
            for r in 0..rows {
                for c in 0..cols {
                    rotated[c][rows - 1 - r] = grid[r][c];
                }
            }
            Ok(rotated)
        }
        180 => {
            let mut rotated = grid.clone();
            rotated.reverse();
            for row in rotated.iter_mut() {
                row.reverse();
            }
            Ok(rotated)
        }
        270 => {
            let rows = grid.len();
            let cols = grid[0].len();
            let mut rotated = vec![vec![0; rows]; cols];
            for r in 0..rows {
                for c in 0..cols {
                    rotated[cols - 1 - c][r] = grid[r][c];
                }
            }
            Ok(rotated)
        }
        _ => Ok(grid),
    }
}

#[pyfunction]
fn reflect_grid(grid: Vec<Vec<u8>>, axis: String) -> PyResult<Vec<Vec<u8>>> {
    let mut reflected = grid.clone();
    if axis == "x" {
        reflected.reverse();
    } else if axis == "y" {
        for row in reflected.iter_mut() {
            row.reverse();
        }
    }
    Ok(reflected)
}

#[pyfunction]
fn scale_grid(grid: Vec<Vec<u8>>, factor: usize) -> PyResult<Vec<Vec<u8>>> {
    let mut new_grid = Vec::new();
    for row in grid {
        let mut new_row = Vec::with_capacity(row.len() * factor);
        for &val in &row {
            for _ in 0..factor {
                new_row.push(val);
            }
        }
        for _ in 0..factor {
            new_grid.push(new_row.clone());
        }
    }
    Ok(new_grid)
}

#[pyfunction]
fn get_objects(grid: Vec<Vec<u8>>) -> PyResult<Vec<PyObject>> {
    let rows = grid.len();
    if rows == 0 { return Ok(Vec::new()); }
    let cols = grid[0].len();
    let mut visited = HashSet::new();
    let mut objects = Vec::new();

    Python::with_gil(|py| {
        for r in 0..rows {
            for c in 0..cols {
                if grid[r][c] != 0 && !visited.contains(&(r, c)) {
                    let color = grid[r][c];
                    let mut pixels = Vec::new();
                    let mut queue = std::collections::VecDeque::new();
                    queue.push_back((r, c));
                    visited.insert((r, c));

                    let (mut min_r, mut max_r) = (r, r);
                    let (mut min_c, mut max_c) = (c, c);

                    while let Some((curr_r, curr_c)) = queue.pop_front() {
                        pixels.push((curr_r, curr_c));
                        min_r = min_r.min(curr_r);
                        max_r = max_r.max(curr_r);
                        min_c = min_c.min(curr_c);
                        max_c = max_c.max(curr_c);

                        for (dr, dc) in &[(0, 1), (0, -1), (1, 0), (-1, 0)] {
                            let nr = curr_r as i32 + dr;
                            let nc = curr_c as i32 + dc;

                            if nr >= 0 && (nr as usize) < rows && nc >= 0 && (nc as usize) < cols {
                                let (unr, unc) = (nr as usize, nc as usize);
                                if grid[unr][unc] == color && !visited.contains(&(unr, unc)) {
                                    visited.insert((unr, unc));
                                    queue.push_back((unr, unc));
                                }
                            }
                        }
                    }

                    let dict = pyo3::types::PyDict::new(py);
                    dict.set_item("color", color)?;
                    dict.set_item("pixels", pixels)?;
                    dict.set_item("bounds", (min_c, min_r, max_c - min_c + 1, max_r - min_r + 1))?;
                    objects.push(dict.to_object(py));
                }
            }
        }
        Ok(objects)
    })
}

#[pymodule]
fn cortex_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(move_grid, m)?)?;
    m.add_function(wrap_pyfunction!(rotate_grid, m)?)?;
    m.add_function(wrap_pyfunction!(reflect_grid, m)?)?;
    m.add_function(wrap_pyfunction!(scale_grid, m)?)?;
    m.add_function(wrap_pyfunction!(get_objects, m)?)?;
    Ok(())
}
