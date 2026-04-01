use alloy::primitives::{Address, Bytes};
use alloy::sol;

// Empleamos macros de sol! para auto-generar los códecs de Rust hacia el contrato BaseStrike.huff
sol! {
    /// Definición de la llamada EOA que enviará el Bot al Proxy/Address del contrato
    /// Equivalente al `function strike(address, bytes) payable` en Huff.
    #[derive(Debug)]
    function strike(address target_dex, bytes calldata payload);
    
    /// Estructura modelo para el swap_data de Aerodrome (v3)
    #[derive(Debug)]
    struct AerodromeExactInputParams {
        bytes path;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
    }
}
