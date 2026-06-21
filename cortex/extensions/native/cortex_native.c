#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <sys/socket.h>
#include <unistd.h>

// C5-REAL Sovereign Guard: Validates Taint Signature in C before GC overhead
static int verify_cortex_taint(const char *buffer, Py_ssize_t size) {
    // Basic verification stub for PoC.
    // In production, invoke hashlib/OpenSSL C-API for SHA3-256.
    if (size > 12 && strncmp(buffer, "taint:", 6) == 0) {
        return 1;
    }
    return 0; 
}

static PyObject* cortex_read_socket_direct(PyObject *self, PyObject *args) {
    int fd;
    Py_ssize_t max_size;
    
    // Extract file descriptor and max buffer size
    if (!PyArg_ParseTuple(args, "in", &fd, &max_size)) {
        return NULL;
    }

    // Direct C-memory allocation, bypassing Python's `bytes` creation
    char *buffer = (char *)PyMem_Malloc(max_size);
    if (buffer == NULL) return PyErr_NoMemory();

    ssize_t bytes_read = read(fd, buffer, max_size);
    
    if (bytes_read < 0) {
        PyMem_Free(buffer);
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    // Cryptographic validation at the metal layer
    if (!verify_cortex_taint(buffer, bytes_read)) {
        PyMem_Free(buffer);
        PyErr_SetString(PyExc_PermissionError, "[CORTEX-TAINT] Invalid Signature. Sovereign Socket Guard blocked ingress.");
        return NULL;
    }

    // Pass valid payload to Python
    PyObject *result = PyBytes_FromStringAndSize(buffer, bytes_read);
    PyMem_Free(buffer);
    
    return result;
}

static PyMethodDef CortexNativeMethods[] = {
    {"read_socket_direct", cortex_read_socket_direct, METH_VARARGS, "Directly read socket FD into C memory, verifying CORTEX-TAINT."},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef cortexnativemodule = {
    PyModuleDef_HEAD_INIT,
    "cortex_native",
    "CORTEX Persist Native Epistemic Guards",
    -1,
    CortexNativeMethods
};

PyMODINIT_FUNC PyInit_cortex_native(void) {
    return PyModule_Create(&cortexnativemodule);
}
