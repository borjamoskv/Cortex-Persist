;;; -*- Mode: LISP; Syntax: COMMON-LISP; Package: LISP-ENGINE.COLLISION; Base: 10 -*-
;;; [C5-REAL] Exergy-Maximized
;;; Author: borjamoskv

(in-package :lisp-engine.collision)

;; Macros de álgebra lineal inline para evitar consing y optimizar registros de CPU
(declaim (inline dot-product))
(defun dot-product (u v)
  (declare (type vec3 u v)
           (optimize (speed 3) (safety 0)))
  (+ (* (aref u 0) (aref v 0))
     (* (aref u 1) (aref v 1))
     (* (aref u 2) (aref v 2))))

(declaim (inline vec-subtract))
(defun vec-subtract (res u v)
  (declare (type vec3 res u v)
           (optimize (speed 3) (safety 0)))
  (setf (aref res 0) (- (aref u 0) (aref v 0)))
  (setf (aref res 1) (- (aref u 1) (aref v 1)))
  (setf (aref res 2) (- (aref u 2) (aref v 2)))
  res)

;; Retorna una columna de la matriz de rotación 3x3 plana
(declaim (inline get-column))
(defun get-column (res mat col)
  (declare (type mat3 mat)
           (type vec3 res)
           (type (integer 0 2) col)
           (optimize (speed 3) (safety 0)))
  (setf (aref res 0) (aref mat (+ col 0)))
  (setf (aref res 1) (aref mat (+ col 3)))
  (setf (aref res 2) (aref mat (+ col 6)))
  res)

;; 1. Intersección AABB vs AABB
(defun intersect-aabb-aabb-p (a b)
  (declare (type aabb a b)
           (optimize (speed 3) (safety 0)))
  (let ((a-min (aabb-min a))
        (a-max (aabb-max a))
        (b-min (aabb-min b))
        (b-max (aabb-max b)))
    (and (and (<= (aref a-min 0) (aref b-max 0)) (>= (aref a-max 0) (aref b-min 0)))
         (and (<= (aref a-min 1) (aref b-max 1)) (>= (aref a-max 1) (aref b-min 1)))
         (and (<= (aref a-min 2) (aref b-max 2)) (>= (aref a-max 2) (aref b-min 2))))))

;; 2. Intersección OBB vs OBB usando Separating Axis Theorem (SAT)
;; Implementación unrolled para garantizar cero consing (0 bytes allocated en Heap)
(defun intersect-obb-obb-p (a b)
  (declare (type obb a b)
           (optimize (speed 3) (safety 0)))
  (let* ((a-center (obb-center a))
         (b-center (obb-center b))
         (a-axes (obb-axes a))
         (b-axes (obb-axes b))
         (a-extents (obb-extents a))
         (b-extents (obb-extents b))
         
         ;; Diferencia de centros
         (t-x (- (aref b-center 0) (aref a-center 0)))
         (t-y (- (aref b-center 1) (aref a-center 1)))
         (t-z (- (aref b-center 2) (aref a-center 2)))
         
         ;; Extraer componentes de los ejes de A (columnas de la matriz)
         (a-u0-x (aref a-axes 0)) (a-u0-y (aref a-axes 3)) (a-u0-z (aref a-axes 6))
         (a-u1-x (aref a-axes 1)) (a-u1-y (aref a-axes 4)) (a-u1-z (aref a-axes 7))
         (a-u2-x (aref a-axes 2)) (a-u2-y (aref a-axes 5)) (a-u2-z (aref a-axes 8))
         
         ;; Extraer componentes de los ejes de B (columnas de la matriz)
         (b-u0-x (aref b-axes 0)) (b-u0-y (aref b-axes 3)) (b-u0-z (aref b-axes 6))
         (b-u1-x (aref b-axes 1)) (b-u1-y (aref b-axes 4)) (b-u1-z (aref b-axes 7))
         (b-u2-x (aref b-axes 2)) (b-u2-y (aref b-axes 5)) (b-u2-z (aref b-axes 8)))
    
    (declare (type single-float t-x t-y t-z
                   a-u0-x a-u0-y a-u0-z a-u1-x a-u1-y a-u1-z a-u2-x a-u2-y a-u2-z
                   b-u0-x b-u0-y b-u0-z b-u1-x b-u1-y b-u1-z b-u2-x b-u2-y b-u2-z))
    
    ;; Calcular matriz de rotación relativa R_ij = dot(A_i, B_j)
    (let* ((r00 (+ (* a-u0-x b-u0-x) (* a-u0-y b-u0-y) (* a-u0-z b-u0-z)))
           (r01 (+ (* a-u0-x b-u1-x) (* a-u0-y b-u1-y) (* a-u0-z b-u1-z)))
           (r02 (+ (* a-u0-x b-u2-x) (* a-u0-y b-u2-y) (* a-u0-z b-u2-z)))
           
           (r10 (+ (* a-u1-x b-u0-x) (* a-u1-y b-u0-y) (* a-u1-z b-u0-z)))
           (r11 (+ (* a-u1-x b-u1-x) (* a-u1-y b-u1-y) (* a-u1-z b-u1-z)))
           (r12 (+ (* a-u1-x b-u2-x) (* a-u1-y b-u2-y) (* a-u1-z b-u2-z)))
           
           (r20 (+ (* a-u2-x b-u0-x) (* a-u2-y b-u0-y) (* a-u2-z b-u0-z)))
           (r21 (+ (* a-u2-x b-u1-x) (* a-u2-y b-u1-y) (* a-u2-z b-u1-z)))
           (r22 (+ (* a-u2-x b-u2-x) (* a-u2-y b-u2-y) (* a-u2-z b-u2-z)))
           
           ;; Valores absolutos de la matriz R con epsilon para evitar singularidades
           (ar00 (+ (abs r00) 1.0f-6)) (ar01 (+ (abs r01) 1.0f-6)) (ar02 (+ (abs r02) 1.0f-6))
           (ar10 (+ (abs r10) 1.0f-6)) (ar11 (+ (abs r11) 1.0f-6)) (ar12 (+ (abs r12) 1.0f-6))
           (ar20 (+ (abs r20) 1.0f-6)) (ar21 (+ (abs r21) 1.0f-6)) (ar22 (+ (abs r22) 1.0f-6)))
      
      (declare (type single-float r00 r01 r02 r10 r11 r12 r20 r21 r22
                     ar00 ar01 ar02 ar10 ar11 ar12 ar20 ar21 ar22))
      
      (let ((ra 0.0f0) (rb 0.0f0) (t-val 0.0f0))
        (declare (type single-float ra rb t-val))
        
        ;; 1. Test de los 3 ejes de A
        ;; Eje A0
        (setf ra (aref a-extents 0))
        (setf rb (+ (* (aref b-extents 0) ar00) (* (aref b-extents 1) ar01) (* (aref b-extents 2) ar02)))
        (setf t-val (abs (+ (* t-x a-u0-x) (* t-y a-u0-y) (* t-z a-u0-z))))
        (when (> t-val (+ ra rb)) (return-from intersect-obb-obb-p nil))
        
        ;; Eje A1
        (setf ra (aref a-extents 1))
        (setf rb (+ (* (aref b-extents 0) ar10) (* (aref b-extents 1) ar11) (* (aref b-extents 2) ar12)))
        (setf t-val (abs (+ (* t-x a-u1-x) (* t-y a-u1-y) (* t-z a-u1-z))))
        (when (> t-val (+ ra rb)) (return-from intersect-obb-obb-p nil))
        
        ;; Eje A2
        (setf ra (aref a-extents 2))
        (setf rb (+ (* (aref b-extents 0) ar20) (* (aref b-extents 1) ar21) (* (aref b-extents 2) ar22)))
        (setf t-val (abs (+ (* t-x a-u2-x) (* t-y a-u2-y) (* t-z a-u2-z))))
        (when (> t-val (+ ra rb)) (return-from intersect-obb-obb-p nil))
        
        ;; 2. Test de los 3 ejes de B
        ;; Eje B0
        (setf ra (+ (* (aref a-extents 0) ar00) (* (aref a-extents 1) ar10) (* (aref a-extents 2) ar20)))
        (setf rb (aref b-extents 0))
        (setf t-val (abs (+ (* t-x b-u0-x) (* t-y b-u0-y) (* t-z b-u0-z))))
        (when (> t-val (+ ra rb)) (return-from intersect-obb-obb-p nil))
        
        ;; Eje B1
        (setf ra (+ (* (aref a-extents 0) ar01) (* (aref a-extents 1) ar11) (* (aref a-extents 2) ar21)))
        (setf rb (aref b-extents 1))
        (setf t-val (abs (+ (* t-x b-u1-x) (* t-y b-u1-y) (* t-z b-u1-z))))
        (when (> t-val (+ ra rb)) (return-from intersect-obb-obb-p nil))
        
        ;; Eje B2
        (setf ra (+ (* (aref a-extents 0) ar02) (* (aref a-extents 1) ar12) (* (aref a-extents 2) ar22)))
        (setf rb (aref b-extents 2))
        (setf t-val (abs (+ (* t-x b-u2-x) (* t-y b-u2-y) (* t-z b-u2-z))))
        (when (> t-val (+ ra rb)) (return-from intersect-obb-obb-p nil))
        
        ;; 3. Test de los 9 ejes cruzados
        ;; Eje A0 x B0
        (setf ra (+ (* (aref a-extents 1) ar20) (* (aref a-extents 2) ar10)))
        (setf rb (+ (* (aref b-extents 1) ar02) (* (aref b-extents 2) ar01)))
        (setf t-val (abs (- (* (+ (* t-x a-u2-x) (* t-y a-u2-y) (* t-z a-u2-z)) r10)
                            (* (+ (* t-x a-u1-x) (* t-y a-u1-y) (* t-z a-u1-z)) r20))))
        (when (> t-val (+ ra rb)) (return-from intersect-obb-obb-p nil))
        
        ;; Eje A0 x B1
        (setf ra (+ (* (aref a-extents 1) ar21) (* (aref a-extents 2) ar11)))
        (setf rb (+ (* (aref b-extents 0) ar02) (* (aref b-extents 2) ar00)))
        (setf t-val (abs (- (* (+ (* t-x a-u2-x) (* t-y a-u2-y) (* t-z a-u2-z)) r11)
                            (* (+ (* t-x a-u1-x) (* t-y a-u1-y) (* t-z a-u1-z)) r22))))
        (when (> t-val (+ ra rb)) (return-from intersect-obb-obb-p nil))
        
        ;; Eje A0 x B2
        (setf ra (+ (* (aref a-extents 1) ar22) (* (aref a-extents 2) ar12)))
        (setf rb (+ (* (aref b-extents 0) ar01) (* (aref b-extents 1) ar00)))
        (setf t-val (abs (- (* (+ (* t-x a-u2-x) (* t-y a-u2-y) (* t-z a-u2-z)) r12)
                            (* (+ (* t-x a-u1-x) (* t-y a-u1-y) (* t-z a-u1-z)) r21))))
        (when (> t-val (+ ra rb)) (return-from intersect-obb-obb-p nil))
        
        ;; Eje A1 x B0
        (setf ra (+ (* (aref a-extents 0) ar20) (* (aref a-extents 2) ar00)))
        (setf rb (+ (* (aref b-extents 1) ar12) (* (aref b-extents 2) ar11)))
        (setf t-val (abs (- (* (+ (* t-x a-u0-x) (* t-y a-u0-y) (* t-z a-u0-z)) r20)
                            (* (+ (* t-x a-u2-x) (* t-y a-u2-y) (* t-z a-u2-z)) r00))))
        (when (> t-val (+ ra rb)) (return-from intersect-obb-obb-p nil))
        
        ;; Eje A1 x B1
        (setf ra (+ (* (aref a-extents 0) ar21) (* (aref a-extents 2) ar01)))
        (setf rb (+ (* (aref b-extents 0) ar12) (* (aref b-extents 2) ar10)))
        (setf t-val (abs (- (* (+ (* t-x a-u0-x) (* t-y a-u0-y) (* t-z a-u0-z)) r21)
                            (* (+ (* t-x a-u2-x) (* t-y a-u2-y) (* t-z a-u2-z)) r01))))
        (when (> t-val (+ ra rb)) (return-from intersect-obb-obb-p nil))
        
        ;; Eje A1 x B2
        (setf ra (+ (* (aref a-extents 0) ar22) (* (aref a-extents 2) ar02)))
        (setf rb (+ (* (aref b-extents 0) ar11) (* (aref b-extents 1) ar10)))
        (setf t-val (abs (- (* (+ (* t-x a-u0-x) (* t-y a-u0-y) (* t-z a-u0-z)) r22)
                            (* (+ (* t-x a-u2-x) (* t-y a-u2-y) (* t-z a-u2-z)) r02))))
        (when (> t-val (+ ra rb)) (return-from intersect-obb-obb-p nil))
        
        ;; Eje A2 x B0
        (setf ra (+ (* (aref a-extents 0) ar10) (* (aref a-extents 1) ar00)))
        (setf rb (+ (* (aref b-extents 1) ar22) (* (aref b-extents 2) ar21)))
        (setf t-val (abs (- (* (+ (* t-x a-u1-x) (* t-y a-u1-y) (* t-z a-u1-z)) r00)
                            (* (+ (* t-x a-u0-x) (* t-y a-u0-y) (* t-z a-u0-z)) r10))))
        (when (> t-val (+ ra rb)) (return-from intersect-obb-obb-p nil))
        
        ;; Eje A2 x B1
        (setf ra (+ (* (aref a-extents 0) ar11) (* (aref a-extents 1) ar01)))
        (setf rb (+ (* (aref b-extents 0) ar22) (* (aref b-extents 2) ar20)))
        (setf t-val (abs (- (* (+ (* t-x a-u1-x) (* t-y a-u1-y) (* t-z a-u1-z)) r01)
                            (* (+ (* t-x a-u0-x) (* t-y a-u0-y) (* t-z a-u0-z)) r11))))
        (when (> t-val (+ ra rb)) (return-from intersect-obb-obb-p nil))
        
        ;; Eje A2 x B2
        (setf ra (+ (* (aref a-extents 0) ar12) (* (aref a-extents 1) ar02)))
        (setf rb (+ (* (aref b-extents 0) ar21) (* (aref b-extents 1) ar20)))
        (setf t-val (abs (- (* (+ (* t-x a-u1-x) (* t-y a-u1-y) (* t-z a-u1-z)) r02)
                            (* (+ (* t-x a-u0-x) (* t-y a-u0-y) (* t-z a-u0-z)) r12))))
        (when (> t-val (+ ra rb)) (return-from intersect-obb-obb-p nil))
        
        t))))

;; 3. Intersección Ray vs OBB
(defun intersect-ray-obb-p (ry o)
  (declare (type ray ry)
           (type obb o)
           (optimize (speed 3) (safety 0)))
  (let ((t-min 0.0f0)
        (t-max most-positive-single-float)
        (o-center (obb-center o))
        (o-axes (obb-axes o))
        (o-extents (obb-extents o))
        (ray-origin (ray-origin ry))
        (ray-direction (ray-direction ry)))
    (declare (type single-float t-min t-max))
    
    (let ((p-x (- (aref ray-origin 0) (aref o-center 0)))
          (p-y (- (aref ray-origin 1) (aref o-center 1)))
          (p-z (- (aref ray-origin 2) (aref o-center 2))))
      (declare (type single-float p-x p-y p-z))
      
      (loop for i from 0 to 2 do
           (let ((u-x (aref o-axes (+ i 0)))
                 (u-y (aref o-axes (+ i 3)))
                 (u-z (aref o-axes (+ i 6)))
                 (extent (aref o-extents i)))
             (declare (type single-float u-x u-y u-z extent))
             (let ((e (+ (* u-x p-x) (* u-y p-y) (* u-z p-z)))
                   (f (+ (* u-x (aref ray-direction 0))
                         (* u-y (aref ray-direction 1))
                         (* u-z (aref ray-direction 2)))))
               (declare (type single-float e f))
               (if (> (abs f) 1.0f-6)
                   (let ((t1 (/ (- (- extent) e) f))
                         (t2 (/ (- extent e) f)))
                     (declare (type single-float t1 t2))
                     (when (> t1 t2)
                       (rotatef t1 t2))
                     (when (> t1 t-min)
                       (setf t-min t1))
                     (when (< t2 t-max)
                       (setf t-max t2))
                     (when (> t-min t-max)
                       (return-from intersect-ray-obb-p nil))
                     (when (< t-max 0.0f0)
                       (return-from intersect-ray-obb-p nil)))
                   (when (or (< (+ e extent) 0.0f0) (> (- e extent) 0.0f0))
                     (return-from intersect-ray-obb-p nil))))))
      t)))
