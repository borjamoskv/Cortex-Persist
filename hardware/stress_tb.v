/*
 * ∴ SOVEREIGN LEDGER VALIDATOR TESTBENCH v1.2
 * Verifies Silicon Truth Invariants & Entropy Immunity (LGD-200)
 */

`timescale 1ns/1ps

module stress_tb;
    parameter HASH_WIDTH = 256;
    
    reg clk;
    reg rst_n;
    reg start_validation;
    reg [31:0] entropy_injection;
    reg [HASH_WIDTH-1:0] prev_hash_in;
    reg [HASH_WIDTH-1:0] hash_in;
    reg [31:0] actor_permissions;
    reg [31:0] required_permissions;
    
    wire done;
    wire valid;
    wire [3:0] status_code;
    wire [31:0] validated_event_count;
    wire chain_error;
    wire hash_error;
    wire permission_error;
    wire entropy_alarm;
    
    // Instantiate UUT
    sovereign_ledger_validator #(
        .HASH_WIDTH(HASH_WIDTH)
    ) uut (
        .clk(clk),
        .rst_n(rst_n),
        .start_validation(start_validation),
        .entropy_injection(entropy_injection),
        .prev_hash_in(prev_hash_in),
        .hash_in(hash_in),
        .actor_permissions(actor_permissions),
        .required_permissions(required_permissions),
        .done(done),
        .valid(valid),
        .status_code(status_code),
        .validated_event_count(validated_event_count),
        .chain_error(chain_error),
        .hash_error(hash_error),
        .permission_error(permission_error),
        .entropy_alarm(entropy_alarm)
    );

    // Clock generation: 100MHz (10ns period)
    initial clk = 0;
    always #5 clk = ~clk;
    
    // Debugging trace
    always @(posedge clk) begin
        $display("[TB TRACE] Time=%0t clk=%b rst_n=%b start=%b state=%h done=%b valid=%b count=%d error=%b alarm=%b",
                 $time, clk, rst_n, start_validation, status_code, done, valid, validated_event_count,
                 (chain_error || hash_error || permission_error), entropy_alarm);
    end

    initial begin
        $dumpfile("hardware/stress_tb.vcd");
        $dumpvars(0, stress_tb);
    end

    // Helper task to pulse start_validation cleanly
    task trigger_validation;
        begin
            @(posedge clk);
            #1;
            start_validation = 1;
            @(posedge clk);
            #1;
            start_validation = 0;
        end
    endtask

    // Capture registers for outputs sampled exactly on the done clock edge
    reg test_valid;
    reg [31:0] test_count;
    reg test_chain_error;
    reg test_hash_error;
    reg test_permission_error;
    reg test_entropy_alarm;

    // Tasks for validating
    task wait_done;
        begin
            @(posedge clk);
            while (!done) @(posedge clk);
            // Capture output state at the posedge where done is high
            test_valid = valid;
            test_count = validated_event_count;
            test_chain_error = chain_error;
            test_hash_error = hash_error;
            test_permission_error = permission_error;
            test_entropy_alarm = entropy_alarm;
            #1; // slight offset to clear task state safely
        end
    endtask
    
    integer passes = 0;
    integer failures = 0;
    
    initial begin
        $display("  ∴ INITIATING LGD-200 SILICON STRESS TEST...");
        
        // Reset state
        rst_n = 0;
        start_validation = 0;
        entropy_injection = 32'h0;
        prev_hash_in = 256'h0;
        hash_in = 256'h0;
        actor_permissions = 32'h0;
        required_permissions = 32'h0;
        
        #25;
        rst_n = 1;
        #15;
        
        // ==========================================
        // TEST 1: Genesis block validation (passes)
        // ==========================================
        #1;
        prev_hash_in = 256'h0000000000000000000000000000000000000000000000000000000000000000;
        hash_in      = 256'hAAAA111100000000000000000000000000000000000000000000000000000000;
        actor_permissions = 32'h00000001;
        required_permissions = 32'h00000001;
        entropy_injection = 32'h0;
        
        trigger_validation();
        wait_done();
        
        if (test_valid == 1 && test_count == 1 && test_chain_error == 0 && test_hash_error == 0 && test_permission_error == 0 && test_entropy_alarm == 0) begin
            $display("  [✓] TEST 1 PASS: Genesis block validated successfully.");
            passes = passes + 1;
        end else begin
            $display("  [✗] TEST 1 FAIL: Genesis validation failed. count=%d, valid=%b", test_count, test_valid);
            failures = failures + 1;
        end
        #10;

        // ==========================================
        // TEST 2: Sequential block 1 validation (passes)
        // ==========================================
        #1;
        prev_hash_in = 256'hAAAA111100000000000000000000000000000000000000000000000000000000;
        hash_in      = 256'hBBBB222200000000000000000000000000000000000000000000000000000000;
        actor_permissions = 32'h00000001;
        required_permissions = 32'h00000001;
        
        trigger_validation();
        wait_done();
        
        if (test_valid == 1 && test_count == 2 && test_chain_error == 0) begin
            $display("  [✓] TEST 2 PASS: Sequential block 1 verified.");
            passes = passes + 1;
        end else begin
            $display("  [✗] TEST 2 FAIL: Seq 1 verification failed.");
            failures = failures + 1;
        end
        #10;

        // ==========================================
        // TEST 3: Sequential block 2 validation (passes)
        // ==========================================
        #1;
        prev_hash_in = 256'hBBBB222200000000000000000000000000000000000000000000000000000000;
        hash_in      = 256'hCCCC333300000000000000000000000000000000000000000000000000000000;
        actor_permissions = 32'h00000001;
        required_permissions = 32'h00000001;
        
        trigger_validation();
        wait_done();
        
        if (test_valid == 1 && test_count == 3 && test_chain_error == 0) begin
            $display("  [✓] TEST 3 PASS: Sequential block 2 verified.");
            passes = passes + 1;
        end else begin
            $display("  [✗] TEST 3 FAIL: Seq 2 verification failed.");
            failures = failures + 1;
        end
        #10;

        // ==========================================
        // TEST 4: Broken chain linkage validation (chain_error)
        // ==========================================
        #1;
        prev_hash_in = 256'hDEADBEEF00000000000000000000000000000000000000000000000000000000; // mismatch
        hash_in      = 256'hDDDD444400000000000000000000000000000000000000000000000000000000;
        actor_permissions = 32'h00000001;
        required_permissions = 32'h00000001;
        
        trigger_validation();
        wait_done();
        
        if (test_valid == 0 && test_chain_error == 1 && test_count == 3) begin
            $display("  [✓] TEST 4 PASS: Broken chain link correctly detected & rejected.");
            passes = passes + 1;
        end else begin
            $display("  [✗] TEST 4 FAIL: Broken link check bypassed! valid=%b, chain_err=%b", test_valid, test_chain_error);
            failures = failures + 1;
        end
        #10;

        // ==========================================
        // TEST 5: Recovery test (passes)
        // ==========================================
        #1;
        prev_hash_in = 256'hCCCC333300000000000000000000000000000000000000000000000000000000; // correct
        hash_in      = 256'hDDDD444400000000000000000000000000000000000000000000000000000000;
        actor_permissions = 32'h00000001;
        required_permissions = 32'h00000001;
        
        trigger_validation();
        wait_done();
        
        if (test_valid == 1 && test_count == 4 && test_chain_error == 0) begin
            $display("  [✓] TEST 5 PASS: Validator successfully recovered chain linkage.");
            passes = passes + 1;
        end else begin
            $display("  [✗] TEST 5 FAIL: Recovery failed.");
            failures = failures + 1;
        end
        #10;

        // ==========================================
        // TEST 6: Permission check pass (passes)
        // ==========================================
        #1;
        prev_hash_in = 256'hDDDD444400000000000000000000000000000000000000000000000000000000;
        hash_in      = 256'hEEEE555500000000000000000000000000000000000000000000000000000000;
        actor_permissions = 32'h0000FFFF;
        required_permissions = 32'h000000FF;
        
        trigger_validation();
        wait_done();
        
        if (test_valid == 1 && test_count == 5 && test_permission_error == 0) begin
            $display("  [✓] TEST 6 PASS: Multi-bit permission verification succeeded.");
            passes = passes + 1;
        end else begin
            $display("  [✗] TEST 6 FAIL: Perm check pass failed.");
            failures = failures + 1;
        end
        #10;

        // ==========================================
        // TEST 7: Permission check fail (permission_error)
        // ==========================================
        #1;
        prev_hash_in = 256'hEEEE555500000000000000000000000000000000000000000000000000000000;
        hash_in      = 256'hFFFF666600000000000000000000000000000000000000000000000000000000;
        actor_permissions = 32'h0000007F; // Lacks 32'h00000080 bit
        required_permissions = 32'h000000FF;
        
        trigger_validation();
        wait_done();
        
        if (test_valid == 0 && test_permission_error == 1 && test_count == 5) begin
            $display("  [✓] TEST 7 PASS: Insufficient actor permission detected & rejected.");
            passes = passes + 1;
        end else begin
            $display("  [✗] TEST 7 FAIL: Security permission check bypassed.");
            failures = failures + 1;
        end
        #10;

        // ==========================================
        // TEST 8: Corrupt hash validation (hash_error)
        // ==========================================
        #1;
        prev_hash_in = 256'hEEEE555500000000000000000000000000000000000000000000000000000000;
        hash_in      = 256'h0000000000000000000000000000000000000000000000000000000000000000; // corrupt all-zero hash
        actor_permissions = 32'h0000FFFF;
        required_permissions = 32'h00000000;
        
        trigger_validation();
        wait_done();
        
        if (test_valid == 0 && test_hash_error == 1 && test_count == 5) begin
            $display("  [✓] TEST 8 PASS: Malformed zero-hash block detected & rejected.");
            passes = passes + 1;
        end else begin
            $display("  [✗] TEST 8 FAIL: Zero-hash block accepted.");
            failures = failures + 1;
        end
        #10;

        // ==========================================
        // TEST 9: Maximum entropy injection (entropy_alarm)
        // ==========================================
        #1;
        prev_hash_in = 256'hEEEE555500000000000000000000000000000000000000000000000000000000;
        hash_in      = 256'hFFFF777700000000000000000000000000000000000000000000000000000000;
        actor_permissions = 32'hFFFFFFFF;
        required_permissions = 32'h00000000;
        entropy_injection = 32'hFFFFFFFF; // entropy injection trigger
        
        trigger_validation();
        wait_done();
        
        if (test_valid == 0 && test_entropy_alarm == 1 && test_count == 5) begin
            $display("  [✓] TEST 9 PASS: Entropy Injection (32'hFFFFFFFF) triggered alarm & lockout.");
            passes = passes + 1;
        end else begin
            $display("  [✗] TEST 9 FAIL: Entropy injection ignored.");
            failures = failures + 1;
        end
        #10;

        // ==========================================
        // TEST 10: Mid-flight Reset Recovery (passes)
        // ==========================================
        #1;
        prev_hash_in = 256'hEEEE555500000000000000000000000000000000000000000000000000000000;
        hash_in      = 256'hFFFF888800000000000000000000000000000000000000000000000000000000;
        actor_permissions = 32'h00000001;
        required_permissions = 32'h00000001;
        entropy_injection = 32'h0;
        
        // Start validation sequence
        @(posedge clk);
        #1;
        start_validation = 1;
        @(posedge clk);
        #1;
        start_validation = 0;
        
        // Wait 2 clock cycles and assert reset
        @(posedge clk);
        @(posedge clk);
        #1;
        rst_n = 0;
        #25;
        rst_n = 1;
        #15;
        
        // Retry valid block validation
        trigger_validation();
        wait_done();
        
        if (test_valid == 1 && test_count == 1) begin
            $display("  [✓] TEST 10 PASS: Mid-flight reset recovery verified.");
            passes = passes + 1;
        end else begin
            $display("  [✗] TEST 10 FAIL: Mid-flight reset recovery failed. count=%d", test_count);
            failures = failures + 1;
        end
        #10;

        // Final Report
        $display("\n  ∴ SILICON VERIFICATION SUMMARY:");
        $display("    PASSES:   %0d", passes);
        $display("    FAILURES: %0d", failures);
        
        if (failures == 0 && passes == 10) begin
            $display("  ∴ [SYSTEM CONFIRMED] Sovereign Ledger Validator has attained absolute entropy immunity.");
        end else begin
            $display("  ∴ [INTEGRITY BREACH] Stress test failures detected!");
        end
        
        $finish;
    end

endmodule
