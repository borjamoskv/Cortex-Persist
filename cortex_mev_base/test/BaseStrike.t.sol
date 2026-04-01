// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";

contract BaseStrikeTest is Test {
    address huffContract;
    address constant WETH = 0x4200000000000000000000000000000000000006;

    /// @notice Despliega el contrato Huff compilando sobre la marcha mediante FFI
    function setUp() public {
        string[] memory cmds = new string[](3);
        cmds[0] = "huffc";
        cmds[1] = "contracts/BaseStrike.huff";
        cmds[2] = "--bytecode";

        bytes memory bytecode = vm.ffi(cmds);
        
        address deployedAddress;
        assembly {
            deployedAddress := create(0, add(bytecode, 0x20), mload(bytecode))
        }
        require(deployedAddress != address(0), "Huff Deploy Failed");
        huffContract = deployedAddress;
        
        vm.label(huffContract, "BaseStrike_Huff");
    }

    /// @notice Test unitario que fuerza un Revert atómico por falta de Profit
    function test_AtomicRevertOnNoProfit() public {
        // Simulamos un delta de WETH (el bot se queda en 0 y no gana WETH tras el call)
        // El Macro `lt fail jumpi` debe atrapar esto y revertir la transacción O(1).
        
        // Fondeamos el tester
        vm.deal(address(this), 1 ether);
        
        // Ejecutamos strike (DEX ficticio, Payload Cero)
        (bool success, ) = huffContract.call{value: 0}(
            abi.encodeWithSignature("strike(address,bytes)", address(0xDEAD), "")
        );
        
        // Debería fracasar por no tener retorno positivo de WETH (Atomic Revert)
        assertFalse(success, "Huff Atomic Guard Failed to Revert!");
    }
}
