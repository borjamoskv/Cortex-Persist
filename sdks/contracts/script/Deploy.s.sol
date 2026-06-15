// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console} from "forge-std/Script.sol";
import {CortexOracle} from "../src/CortexOracle.sol";
import {CortexLineageRegistry} from "../src/CortexLineageRegistry.sol";

contract DeployCortexOracle is Script {
    function run() public {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address functionsRouter = vm.envAddress("FUNCTIONS_ROUTER");
        bytes32 donId = vm.envBytes32("DON_ID");

        vm.startBroadcast(deployerPrivateKey);

        CortexLineageRegistry registry = new CortexLineageRegistry();
        console.log("CortexLineageRegistry deployed at:", address(registry));

        CortexOracle oracle = new CortexOracle(functionsRouter, donId, address(registry));
        console.log("CortexOracle deployed at:", address(oracle));

        registry.setOracle(address(oracle));
        console.log("CortexOracle authorized in Registry.");

        vm.stopBroadcast();
    }
}
