/*
 * ∴ CORTEX-BALANCE-TESTBENCH v1.0
 * Verifies Silicon Truth Invariants
 */

`timescale 1ns/1ps

module cortex_balance_tb;
    reg clk;
    reg reset_n;
    reg [63:0] current_balance;
    reg [63:0] threshold;
    reg enable;
    
    wire strike_enable;
    wire alert_flag;
    wire [3:0] status_code;

    // Instantiate UUT
    cortex_balance_monitor uut (
        .clk(clk),
        .reset_n(reset_n),
        .current_balance_async(current_balance),
        .threshold_async(threshold),
        .enable_async(enable),
        .strike_enable(strike_enable),
        .alert_flag(alert_flag),
        .status_code(status_code)
    );

    // Clock generation
    initial clk = 0;
    always #5 clk = ~clk;

    initial begin
        // Industrial Noir Verification Sequence
        $display("  ∴ INITIALIZING SILICON VERIFICATION...");
        
        reset_n = 0;
        enable = 0;
        current_balance = 64'h0;
        threshold = 64'h100;
        
        #20 reset_n = 1;
        #20 enable = 1;

        // Test Case 1: Balance < Threshold
        current_balance = 64'h50;
        #30; // Wait for 3 clock cycles (latency is 2)
        if (strike_enable == 0) 
            $display("  [✓] TEST_1 PASS: Balance below threshold correctly inhibited.");
        else
            $display("  [✗] TEST_1 FAIL");

        // Test Case 2: Balance >= Threshold
        current_balance = 64'h150;
        #30;
        if (strike_enable == 1) 
            $display("  [✓] TEST_2 PASS: Strike enabled at exergy threshold.");
        else
            $display("  [✗] TEST_2 FAIL");

        // Test Case 3: Disable
        enable = 0;
        #40;
        if (strike_enable == 0)
            $display("  [✓] TEST_3 PASS: System shutdown verified.");
        else
            $display("  [✗] TEST_3 FAIL");

        $display("  ∴ VERIFICATION COMPLETE. EXITING.");
        $finish;
    end

endmodule
