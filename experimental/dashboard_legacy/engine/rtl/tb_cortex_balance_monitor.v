/*
 * ∴ TB-CORTEX-BALANCE-MONITOR
 * Verification of Law Ω₀ (Silicon Truth)
 */

`timescale 1ns/1ps

module tb_cortex_balance_monitor;

    reg clk;
    reg reset_n;
    reg [63:0] current_balance_async;
    reg [63:0] threshold_async;
    reg enable_async;

    wire strike_enable;
    wire alert_flag;
    wire [3:0] status_code;

    // Instantiate UUT
    cortex_balance_monitor uut (
        .clk(clk),
        .reset_n(reset_n),
        .current_balance_async(current_balance_async),
        .threshold_async(threshold_async),
        .enable_async(enable_async),
        .strike_enable(strike_enable),
        .alert_flag(alert_flag),
        .status_code(status_code)
    );

    // Clock generation
    initial clk = 0;
    always #5 clk = ~clk; // 100MHz

    initial begin
        // Setup dump file for GTKWave
        $dumpfile("strike_sim.vcd");
        $dumpvars(0, tb_cortex_balance_monitor);

        // Initialize signals
        reset_n = 0;
        current_balance_async = 64'd0;
        threshold_async = 64'd1660000; // Total Projected Yield ($1,660,000)
        enable_async = 0;

        #20 reset_n = 1;
        #20 enable_async = 1;

        // Test Case 1: Balance < Threshold
        current_balance_async = 64'd1000000; // Firedancer baseline only
        #50;
        if (status_code == 4'h1) // STATE_SUMMATION (renamed from STATE_COMPARE in UUT)
            $display("[SUCCESS] Law Ω₀ Verification: Balance < Threshold correctly identified.");
        else
            $display("[FAILURE] Law Ω₀ Verification: Unexpected status code %h", status_code);

        // Test Case 2: Balance >= Threshold (STRIKE)
        current_balance_async = 64'd1700000; // Target exceeded ($1.7M)
        #50; 
        if (strike_enable == 1'b1 && status_code == 4'h2) // STATE_TRIGGER
            $display("[SUCCESS] Law Ω₀ Verification: STRIKE PULSE detected at $1.7M yield.");
        else
            $display("[FAILURE] Law Ω₀ Verification: Strike failed to trigger. Balance=%d, Status=%h", current_balance_async, status_code);

        // Test Case 3: Disable
        enable_async = 0;
        #50;
        if (strike_enable == 1'b0)
            $display("[SUCCESS] Law Ω₀ Verification: Safe de-activation verified.");
        else
            $display("[FAILURE] Law Ω₀ Verification: Strike remained active after disable.");

        #10 $finish;
    end

endmodule
