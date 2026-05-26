/*
 * ∴ SOVEREIGN LEDGER VALIDATOR v1.0
 * Law Ω₀: Silicon Truth
 * 
 * Synthesizable RTL for deterministic ledger verification.
 * Target: Lattice iCE40 / Xilinx Artix-7
 * Reality Level: C5-REAL
 */

module sovereign_ledger_validator #(
    parameter HASH_WIDTH = 256
)(
    input wire clk,
    input wire rst_n,
    
    // Control
    input wire start_validation,
    input wire [31:0] entropy_injection,
    
    // Inputs
    input wire [HASH_WIDTH-1:0] prev_hash_in,
    input wire [HASH_WIDTH-1:0] hash_in,
    input wire [31:0] actor_permissions,
    input wire [31:0] required_permissions,
    
    // Outputs
    output reg done,
    output reg valid,
    output reg [3:0] status_code,
    output reg [31:0] validated_event_count,
    
    // Error Flags
    output reg chain_error,
    output reg hash_error,
    output reg permission_error,
    output reg entropy_alarm
);

    // States
    localparam STATE_IDLE         = 4'h0;
    localparam STATE_LATCH        = 4'h1;
    localparam STATE_VERIFY_CHAIN = 4'h2;
    localparam STATE_VERIFY_HASH  = 4'h3;
    localparam STATE_VERIFY_PERM  = 4'h4;
    localparam STATE_COMMIT       = 4'h5;
    localparam STATE_DONE         = 4'h6;
    localparam STATE_CHAIN_ERR    = 4'h8;
    localparam STATE_HASH_ERR     = 4'h9;
    localparam STATE_PERM_ERR     = 4'hA;
    localparam STATE_ENTROPY_ERR  = 4'hB;

    reg [HASH_WIDTH-1:0] last_valid_hash;
    reg [HASH_WIDTH-1:0] prev_hash_r;
    reg [HASH_WIDTH-1:0] hash_r;
    reg [31:0] actor_permissions_r;
    reg [31:0] required_permissions_r;
    reg [31:0] entropy_injection_r;
    
    reg [3:0] state;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= STATE_IDLE;
            last_valid_hash <= {HASH_WIDTH{1'b0}};
            prev_hash_r <= {HASH_WIDTH{1'b0}};
            hash_r <= {HASH_WIDTH{1'b0}};
            actor_permissions_r <= 32'h0;
            required_permissions_r <= 32'h0;
            entropy_injection_r <= 32'h0;
            
            done <= 1'b0;
            valid <= 1'b0;
            status_code <= STATE_IDLE;
            validated_event_count <= 32'h0;
            
            chain_error <= 1'b0;
            hash_error <= 1'b0;
            permission_error <= 1'b0;
            entropy_alarm <= 1'b0;
        end else begin
            status_code <= state;
            case (state)
                STATE_IDLE: begin
                    done <= 1'b0;
                    valid <= 1'b0;
                    chain_error <= 1'b0;
                    hash_error <= 1'b0;
                    permission_error <= 1'b0;
                    entropy_alarm <= 1'b0;
                    if (start_validation) begin
                        state <= STATE_LATCH;
                        prev_hash_r <= prev_hash_in;
                        hash_r <= hash_in;
                        actor_permissions_r <= actor_permissions;
                        required_permissions_r <= required_permissions;
                        entropy_injection_r <= entropy_injection;
                    end
                end
                
                STATE_LATCH: begin
                    if (entropy_injection_r == 32'hFFFFFFFF) begin
                        entropy_alarm <= 1'b1;
                        state <= STATE_ENTROPY_ERR;
                    end else begin
                        state <= STATE_VERIFY_CHAIN;
                    end
                end
                
                STATE_VERIFY_CHAIN: begin
                    if (validated_event_count > 0 && prev_hash_r != last_valid_hash) begin
                        chain_error <= 1'b1;
                        state <= STATE_CHAIN_ERR;
                    end else begin
                        state <= STATE_VERIFY_HASH;
                    end
                end
                
                STATE_VERIFY_HASH: begin
                    if (hash_r == {HASH_WIDTH{1'b0}} || hash_r == {HASH_WIDTH{1'b1}}) begin
                        hash_error <= 1'b1;
                        state <= STATE_HASH_ERR;
                    end else begin
                        state <= STATE_VERIFY_PERM;
                    end
                end
                
                STATE_VERIFY_PERM: begin
                    if ((actor_permissions_r & required_permissions_r) != required_permissions_r) begin
                        permission_error <= 1'b1;
                        state <= STATE_PERM_ERR;
                    end else begin
                        state <= STATE_COMMIT;
                    end
                end
                
                STATE_COMMIT: begin
                    last_valid_hash <= hash_r;
                    validated_event_count <= validated_event_count + 1;
                    valid <= 1'b1;
                    state <= STATE_DONE;
                end
                
                STATE_DONE: begin
                    done <= 1'b1;
                    state <= STATE_IDLE;
                end
                
                STATE_CHAIN_ERR, STATE_HASH_ERR, STATE_PERM_ERR, STATE_ENTROPY_ERR: begin
                    valid <= 1'b0;
                    done <= 1'b1;
                    state <= STATE_IDLE;
                end
                
                default: state <= STATE_IDLE;
            endcase
        end
    end

endmodule
