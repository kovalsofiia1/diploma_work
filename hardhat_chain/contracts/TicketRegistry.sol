// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract TicketRegistry {
    struct Ticket {
        uint256 eventId;
        string seatId;
        bytes32 ticketHash;
        bool used;
    }

    mapping(uint256 => Ticket) private tickets;

    function mintTicket(uint256 tokenId, uint256 eventId, string calldata seatId, bytes32 ticketHash) external {
        require(tickets[tokenId].ticketHash == bytes32(0), "exists");
        tickets[tokenId] = Ticket({
            eventId: eventId,
            seatId: seatId,
            ticketHash: ticketHash,
            used: false
        });
    }

    function getTicket(uint256 tokenId) external view returns (uint256, string memory, bytes32, bool) {
        Ticket memory t = tickets[tokenId];
        return (t.eventId, t.seatId, t.ticketHash, t.used);
    }

    function markUsed(uint256 tokenId) external {
        require(tickets[tokenId].ticketHash != bytes32(0), "missing");
        require(!tickets[tokenId].used, "already used");
        tickets[tokenId].used = true;
    }
}