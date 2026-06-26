// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * ∴ NARO-X v2.0: THE INDUSTRIAL NOIR PROTOCOL (MEV-DRAIN OMEGA)
 * Generative ERC-20 Asset — Automated Market Forging & Anti-Sandwich Mechanics
 */
contract NaroXToken is ERC20, Ownable {
    uint256 public constant TOTAL_SUPPLY = 100_000_000 * 10**18;
    
    // MEV Extraction Constraints
    uint256 public constant BASE_FEE = 1; // 1%
    uint256 public constant MEV_PENALTY_FEE = 30; // 30% tax if bought & sold in the same block!
    
    address public immutable sovereignWallet;
    
    // Anti-MEV State Tracking
    mapping(address => uint256) private _lastTxBlock;

    constructor(address _sovereignWallet) ERC20("Noire", "NOIR") Ownable(msg.sender) {
        require(_sovereignWallet != address(0), "Invalid Wallet");
        sovereignWallet = _sovereignWallet;
        _mint(msg.sender, TOTAL_SUPPLY);
    }

    function transfer(address to, uint256 amount) public override returns (bool) {
        return _transferWithMEVProtection(_msgSender(), to, amount);
    }

    function transferFrom(address from, address to, uint256 amount) public override returns (bool) {
        address spender = _msgSender();
        _spendAllowance(from, spender, amount);
        return _transferWithMEVProtection(from, to, amount);
    }

    /**
     * @dev Asymmetrical MEV Shield: 
     * If a bot buys and sells in the exact same block (Sandwich Attack), they are taxed 30%.
     * That 30% goes straight to the Sovereign Wallet, effectively stealing capital from MEV bots.
     */
    function _transferWithMEVProtection(address from, address to, uint256 amount) internal returns (bool) {
        // Exemptions
        if (from == sovereignWallet || from == owner() || to == owner() || to == sovereignWallet) {
            _transfer(from, to, amount);
            return true;
        }

        uint256 currentBlock = block.number;
        uint256 feePercentage = BASE_FEE;

        // Detect High-Frequency Bot (Same Block TX)
        if (_lastTxBlock[from] == currentBlock) {
            feePercentage = MEV_PENALTY_FEE;
        }

        // Record block
        _lastTxBlock[to] = currentBlock;
        _lastTxBlock[from] = currentBlock;

        uint256 fee = (amount * feePercentage) / 100;
        uint256 transferAmount = amount - fee;

        _transfer(from, sovereignWallet, fee); // Route yield to Sovereign
        _transfer(from, to, transferAmount);

        return true;
    }
}
