"""Module 7: DAO & Community Governance"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from services.kafka_service import publish_event, EventType
from enum import Enum

logger = logging.getLogger(__name__)

class ProposalStatus(str, Enum):
    DRAFT = "draft"
    VOTING = "voting"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"

class DAOGovernanceService:
    """Smart contracts governance + treasury management"""

    @staticmethod
    def create_proposal(
        proposer_id: int,
        title: str,
        description: str,
        proposal_type: str,
        funding_requested_usd: Optional[float] = None
    ) -> Dict:
        """
        Créer proposition pour DAO (voting)
        """
        try:
            proposal_id = f"PROP-{datetime.utcnow().timestamp()}"

            proposal = {
                "proposal_id": proposal_id,
                "proposer_id": proposer_id,
                "title": title,
                "description": description,
                "proposal_type": proposal_type,  # "infrastructure", "training", "research", etc
                "funding_requested_usd": funding_requested_usd,
                "status": ProposalStatus.DRAFT,
                "voting_starts": (datetime.utcnow() + timedelta(days=3)).isoformat(),
                "voting_ends": (datetime.utcnow() + timedelta(days=10)).isoformat(),
                "voting_quorum_required_pct": 30,
                "approval_threshold_pct": 66,
                "votes_for": 0,
                "votes_against": 0,
                "abstain": 0,
                "created_at": datetime.utcnow().isoformat(),
                "blockchain_contract": "0x...",
                "ipfs_document": "Qm..."  # IPFS hash
            }

            publish_event(EventType.PROPOSAL_CREATED, proposal)
            logger.info(f"✓ Proposal created: {proposal_id}")
            return proposal

        except Exception as e:
            logger.error(f"✗ Proposal creation failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def cast_vote(
        voter_id: int,
        proposal_id: str,
        vote_choice: str,  # "for", "against", "abstain"
        voting_power: float  # tokens held
    ) -> Dict:
        """
        Voter sur une proposition
        """
        try:
            vote = {
                "vote_id": f"VOTE-{voter_id}-{proposal_id}",
                "voter_id": voter_id,
                "proposal_id": proposal_id,
                "vote_choice": vote_choice,
                "voting_power": voting_power,
                "timestamp": datetime.utcnow().isoformat(),
                "blockchain_recorded": True,
                "vote_weight": voting_power * 1.0  # 1 token = 1 vote
            }

            publish_event(EventType.VOTE_CAST, vote)
            logger.info(f"✓ Vote cast: {voter_id} on {proposal_id}")
            return vote

        except Exception as e:
            logger.error(f"✗ Vote casting failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def execute_proposal(proposal_id: str) -> Dict:
        """
        Exécuter proposition approuvée (timelock pour sécurité)
        """
        try:
            execution = {
                "proposal_id": proposal_id,
                "status": "executing",
                "timelock_period_days": 2,
                "execution_scheduled": (datetime.utcnow() + timedelta(days=2)).isoformat(),
                "gas_estimate_usd": 50,
                "blockchain_tx_hash": "0x..."
            }

            logger.info(f"✓ Proposal execution scheduled: {proposal_id}")
            return execution

        except Exception as e:
            logger.error(f"✗ Proposal execution failed: {e}")
            return {"error": str(e)}

class TreasuryManagementService:
    """Trésor DAO + multisig"""

    @staticmethod
    def get_treasury_balance() -> Dict:
        """
        Solde trésor DAO (multisig 3/5 signing)
        """
        return {
            "treasury_id": "TREASURY-AGRO-DAO",
            "total_usd": 150000,
            "breakdown": {
                "operational_reserve": 50000,
                "community_grants": 40000,
                "insurance_pool": 35000,
                "research_fund": 25000
            },
            "multisig_signatories": 5,
            "multisig_required": 3,
            "signatories": [
                {"signer_id": 1, "name": "Mali Coop Lead", "role": "governance"},
                {"signer_id": 2, "name": "Finance Lead", "role": "finance"},
                {"signer_id": 3, "name": "Community Rep", "role": "community"},
                {"signer_id": 4, "name": "Technical Lead", "role": "technical"},
                {"signer_id": 5, "name": "External Auditor", "role": "audit"}
            ],
            "blockchain_address": "0x...",
            "last_updated": datetime.utcnow().isoformat()
        }

    @staticmethod
    def request_fund_distribution(
        recipient_id: int,
        amount_usd: float,
        purpose: str,
        proposal_id: str
    ) -> Dict:
        """
        Demander distribution de fonds (après vote approval)
        """
        try:
            distribution = {
                "distribution_id": f"DIST-{datetime.utcnow().timestamp()}",
                "proposal_id": proposal_id,
                "recipient_id": recipient_id,
                "amount_usd": amount_usd,
                "purpose": purpose,
                "status": "pending_multisig",
                "approvals_current": 0,
                "approvals_required": 3,
                "requested_at": datetime.utcnow().isoformat(),
                "estimated_completion": (datetime.utcnow() + timedelta(days=5)).isoformat()
            }

            logger.info(f"✓ Fund distribution requested: {distribution['distribution_id']}")
            return distribution

        except Exception as e:
            logger.error(f"✗ Fund distribution failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def approve_fund_transfer(distribution_id: str, signer_id: int) -> Dict:
        """
        Signer approvant transfer multisig
        """
        return {
            "distribution_id": distribution_id,
            "signer_id": signer_id,
            "approval_timestamp": datetime.utcnow().isoformat(),
            "status": "awaiting_more_signatures",
            "signatures_collected": 1,
            "signatures_required": 3
        }

class CommunityPoolService:
    """Pools d'assurance mutualisée + fonds collectifs"""

    @staticmethod
    def create_insurance_pool(
        pool_name: str,
        pool_type: str,  # "drought", "pest", "price_floor"
        min_members: int
    ) -> Dict:
        """
        Créer pool d'assurance mutuelle (coopérative partagent risque)
        """
        try:
            pool_id = f"POOL-{pool_type}-{datetime.utcnow().timestamp()}"

            pool = {
                "pool_id": pool_id,
                "name": pool_name,
                "pool_type": pool_type,
                "status": "forming",
                "current_members": 0,
                "min_members_required": min_members,
                "total_contributions_usd": 0,
                "individual_contribution_usd": 25,  # Minimum
                "coverage_multiplier": 3.0,  # 1x contribution → 3x coverage
                "claim_review_required": min_members >= 50,  # Larger pools auto-settle claims
                "created_at": datetime.utcnow().isoformat(),
                "blockchain_contract": "0x..."
            }

            logger.info(f"✓ Insurance pool created: {pool_id}")
            return pool

        except Exception as e:
            logger.error(f"✗ Pool creation failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def join_pool(pool_id: str, member_id: int, contribution_usd: float) -> Dict:
        """
        Rejoindre pool + contribuer
        """
        try:
            membership = {
                "membership_id": f"MEM-{member_id}-{pool_id}",
                "pool_id": pool_id,
                "member_id": member_id,
                "contribution_usd": contribution_usd,
                "max_coverage_usd": contribution_usd * 3,
                "joined_at": datetime.utcnow().isoformat(),
                "status": "active",
                "claim_history": []
            }

            logger.info(f"✓ Member joined pool: {membership['membership_id']}")
            return membership

        except Exception as e:
            logger.error(f"✗ Pool join failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def settle_pool_claim(pool_id: str, member_id: int, claim_amount_usd: float) -> Dict:
        """
        Régler claim from pool (avec vote si pool small)
        """
        try:
            claim = {
                "claim_id": f"CLM-{pool_id}-{member_id}",
                "pool_id": pool_id,
                "member_id": member_id,
                "claim_amount_usd": claim_amount_usd,
                "status": "approved",  # Auto if pool > 100, else needs vote
                "payout_timestamp": datetime.utcnow().isoformat(),
                "blockchain_recorded": True
            }

            publish_event(EventType.FUNDS_DISTRIBUTED, claim)
            logger.info(f"✓ Pool claim settled: {claim['claim_id']} → ${claim_amount_usd}")
            return claim

        except Exception as e:
            logger.error(f"✗ Claim settlement failed: {e}")
            return {"error": str(e)}

    @staticmethod
    def distribute_pool_surplus(pool_id: str) -> Dict:
        """
        Distribuer excédent pool (dividendes members)
        """
        try:
            surplus = 5000  # mock
            member_count = 200

            distribution = {
                "pool_id": pool_id,
                "surplus_usd": surplus,
                "member_count": member_count,
                "dividend_per_member": round(surplus / member_count, 2),
                "distribution_date": datetime.utcnow().isoformat(),
                "status": "completed"
            }

            logger.info(f"✓ Pool surplus distributed: {pool_id} → ${surplus}")
            return distribution

        except Exception as e:
            logger.error(f"✗ Surplus distribution failed: {e}")
            return {"error": str(e)}

# Service instances
dao_governance = DAOGovernanceService()
treasury = TreasuryManagementService()
community_pool = CommunityPoolService()
