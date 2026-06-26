/*
 * ∴ CORTEX-BALANCE-MONITOR v1.1
 * Law Ω₀: Silicon Truth (Ternary / BitNet b1.58 style)
 * 
 * Synthesizable RTL for deterministic exergy gating.
 * Target: Lattice iCE40 / Xilinx Artix-7
 */

module cortex_balance_monitor (
    input wire clk,
    input wire reset_n,
    
    // 64-bit fixed point ETH balances
    input wire [63:0] current_balance_async,
    input wire [63:0] threshold_async,
    
    // Control
    input wire enable_async,
    
    // Outputs
    output reg strike_enable,
    output reg alert_flag,
    output reg [3:0] status_code
);

    // Initial CDC Synchronizers (2-stage)
    reg [63:0] balance_s1, balance_s2;
    reg [63:0] threshold_s1, threshold_s2;
    reg enable_s1, enable_s2;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            balance_s1   <= 64'h0; balance_s2   <= 64'h0;
            threshold_s1 <= 64'h0; threshold_s2 <= 64'h0;
            enable_s1    <= 1'b0;  enable_s2    <= 1'b0;
        end else begin
            balance_s1   <= current_balance_async; balance_s2   <= balance_s1;
            threshold_s1 <= threshold_async;       threshold_s2 <= threshold_s1;
            enable_s1    <= enable_async;          enable_s2    <= enable_s1;
        end
    end

    // Internal state
    localparam STATE_IDLE      = 4'h0;
    localparam STATE_SUMMATION = 4'h1;
    localparam STATE_TRIGGER   = 4'h2;
    localparam STATE_ERROR     = 4'hE;

    // Ternary Exergy Gate (BitNet b1.58 style)
    // d = balance - threshold
    wire [64:0] diff = {1'b0, balance_s2} - {1'b0, threshold_s2};
    wire is_positive = !diff[64];

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            strike_enable <= 1'b0;
            alert_flag <= 1'b0;
            status_code <= STATE_IDLE;
        end else if (enable_s2) begin
            if (is_positive) begin
                strike_enable <= 1'b1;
                status_code <= STATE_TRIGGER;
                alert_flag <= 1'b0;
            end else begin
                strike_enable <= 1'b0;
                status_code <= STATE_SUMMATION;
                alert_flag <= 1'b0;
            end
        end else begin
            strike_enable <= 1'b0;
            alert_flag <= 1'b0;
            status_code <= STATE_IDLE;
        end
    end

endmodule
