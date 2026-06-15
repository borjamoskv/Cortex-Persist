// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test, console} from "forge-std/Test.sol";
import {CortexOracle} from "../src/CortexOracle.sol";
import {CortexLineageRegistry} from "../src/CortexLineageRegistry.sol";

contract MockFunctionsRouter {
    function sendRequest(
        uint64 subscriptionId,
        bytes calldata data,
        uint16 dataVersion,
        uint32 callbackGasLimit,
        bytes32 donId
    ) external returns (bytes32) {
        return keccak256(abi.encodePacked(subscriptionId, data, dataVersion, callbackGasLimit, donId));
    }
}

contract CortexOracleTest is Test {
    CortexOracle public oracle;
    CortexLineageRegistry public registry;
    MockFunctionsRouter public mockRouter;
    bytes32 public dummyDonId = bytes32("fun-ethereum-mainnet-1");

    function setUp() public {
        mockRouter = new MockFunctionsRouter();
        registry = new CortexLineageRegistry();
        oracle = new CortexOracle(address(mockRouter), dummyDonId, address(registry));
        registry.setOracle(address(oracle));
    }

    function test_RequestTelemetryVerification() public {
        bytes32 mockHash = keccak256("c5-real-telemetry");
        string memory source = "return Functions.encodeString('verified');";
        
        // Ensure it emits
        vm.expectEmit(false, true, false, true);
        emit CortexOracle.TelemetryVerificationRequested(bytes32(0), mockHash);
        
        bytes32 reqId = oracle.requestTelemetryVerification(source, mockHash, 1, 300000);
        
        assertEq(oracle.lastTelemetryHash(), mockHash);
        assertTrue(reqId != bytes32(0));
    }

    function test_FulfillRequestSuccess() public {
        bytes32 mockHash = keccak256("c5-real-telemetry-success");
        oracle.requestTelemetryVerification("source", mockHash, 1, 300000);

        bytes32 reqId = keccak256("req1");
        
        // The FunctionsClient requires the caller to be the router
        vm.prank(address(mockRouter));
        oracle.handleOracleFulfillment(reqId, hex"01", new bytes(0));
        
        assertTrue(oracle.lastVerificationResult());
        assertTrue(registry.isVerified(mockHash));
        assertTrue(oracle.verifyTelemetry(mockHash, new bytes(0)));
    }

    function test_FulfillRequestFailure() public {
        bytes32 mockHash = keccak256("c5-real-telemetry-failure");
        oracle.requestTelemetryVerification("source", mockHash, 1, 300000);

        bytes32 reqId = keccak256("req2");
        
        // The FunctionsClient requires the caller to be the router
        vm.prank(address(mockRouter));
        oracle.handleOracleFulfillment(reqId, hex"00", new bytes(0));
        
        assertFalse(oracle.lastVerificationResult());
        assertFalse(registry.isVerified(mockHash));
    }
}

