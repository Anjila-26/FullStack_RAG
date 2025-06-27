from typing_extensions import Annotated, TypedDict
from typing import List, Dict, Any, Optional
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field
import json
from loguru import logger

# Initialize Ollama LLM for evaluation
evaluator_llm = ChatOllama(model="llama3", temperature=0)

# Grade schemas for structured output
class CorrectnessGrade(BaseModel):
    """Schema for correctness evaluation"""
    explanation: str = Field(description="Explain your reasoning for the score")
    correct: bool = Field(description="True if the answer is correct, False otherwise")

class RelevanceGrade(BaseModel):
    """Schema for relevance evaluation"""
    explanation: str = Field(description="Explain your reasoning for the score")
    relevant: bool = Field(description="True if the answer is relevant, False otherwise")
    score: int = Field(description="Relevance score from 1-5", ge=1, le=5)

class GroundednessGrade(BaseModel):
    """Schema for groundedness evaluation"""
    explanation: str = Field(description="Explain your reasoning for the score")
    grounded: bool = Field(description="True if the answer is grounded in context, False otherwise")
    hallucination: bool = Field(description="True if answer contains hallucinations, False otherwise")

class RetrievalRelevanceGrade(BaseModel):
    """Schema for retrieval relevance evaluation"""
    explanation: str = Field(description="Explain your reasoning for the score")
    relevant: bool = Field(description="True if retrieved docs are relevant, False otherwise")
    score: int = Field(description="Relevance score from 1-5", ge=1, le=5)

# Evaluation prompts
CORRECTNESS_INSTRUCTIONS = """You are a teacher grading a quiz. You will be given a QUESTION, the GROUND TRUTH (correct) ANSWER, and the STUDENT ANSWER.

Grade criteria:
(1) Grade the student answers based ONLY on their factual accuracy relative to the ground truth answer.
(2) Ensure that the student answer does not contain any conflicting statements.
(3) It is OK if the student answer contains more information than the ground truth answer, as long as it is factually accurate.

Correctness:
- True: The student's answer meets all criteria and is factually accurate
- False: The student's answer contains factual errors or conflicts with ground truth

Explain your reasoning step-by-step before giving your final judgment."""

RELEVANCE_INSTRUCTIONS = """You are evaluating how well a generated response addresses the user's question.

Evaluation criteria:
(1) Does the response directly address the question asked?
(2) Is the response helpful and informative for the user?
(3) Does the response stay on topic and avoid irrelevant information?
(4) Is the response complete enough to satisfy the user's information need?

Scoring scale:
- 5: Perfectly relevant, directly addresses all aspects of the question
- 4: Highly relevant, addresses most aspects with minor gaps
- 3: Moderately relevant, addresses some aspects but missing key points
- 2: Somewhat relevant, tangentially related but doesn't fully address question
- 1: Not relevant, fails to address the question

Provide detailed reasoning for your score."""

GROUNDEDNESS_INSTRUCTIONS = """You are evaluating whether a generated response is grounded in the provided context.

Evaluation criteria:
(1) Are all claims in the response supported by the retrieved context?
(2) Does the response avoid making statements not found in the context?
(3) Are there any hallucinations or fabricated information?
(4) Does the response accurately represent the information from the context?

Definitions:
- Grounded: All information in the response can be traced back to the provided context
- Hallucination: Information that is not present in or contradicts the provided context

Analyze each claim in the response against the context before making your judgment."""

RETRIEVAL_RELEVANCE_INSTRUCTIONS = """You are evaluating how relevant the retrieved documents are for answering the given question.

Evaluation criteria:
(1) Do the retrieved documents contain information that can help answer the question?
(2) How closely do the documents match the topic and intent of the question?
(3) Would these documents enable someone to provide a good answer to the question?
(4) Are the documents focused on the right subject matter?

Scoring scale:
- 5: Highly relevant, documents directly address the question topic
- 4: Very relevant, documents contain useful information for the question
- 3: Moderately relevant, some useful information but not comprehensive
- 2: Somewhat relevant, tangentially related but limited usefulness
- 1: Not relevant, documents don't help answer the question

Consider the quality and relevance of ALL retrieved documents in your evaluation."""

class RAGEvaluator:
    """Comprehensive RAG evaluation system using Ollama"""
    
    def __init__(self, model_name: str = "llama3", temperature: float = 0):
        self.llm = ChatOllama(model=model_name, temperature=temperature)
        logger.info(f"Initialized RAG Evaluator with model: {model_name}")
    
    def _parse_structured_output(self, response: str, schema_class) -> Dict:
        """Parse LLM response into structured format"""
        try:
            # Try to extract JSON from the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)
                return schema_class(**data).dict()
        except Exception as e:
            logger.warning(f"Failed to parse structured output: {e}")
        
        # Fallback: manual parsing
        return self._manual_parse(response, schema_class)
    
    def _manual_parse(self, response: str, schema_class) -> Dict:
        """Manual parsing fallback"""
        result = {}
        
        # Extract explanation
        if "explanation" in response.lower():
            explanation_start = response.lower().find("explanation")
            explanation_part = response[explanation_start:].split('\n')[0]
            result["explanation"] = explanation_part.split(':', 1)[1].strip() if ':' in explanation_part else response
        else:
            result["explanation"] = response
        
        # Extract boolean values
        response_lower = response.lower()
        if "correct" in schema_class.__fields__:
            result["correct"] = "true" in response_lower and "false" not in response_lower
        if "relevant" in schema_class.__fields__:
            result["relevant"] = "true" in response_lower and "false" not in response_lower
        if "grounded" in schema_class.__fields__:
            result["grounded"] = "true" in response_lower and "false" not in response_lower
        if "hallucination" in schema_class.__fields__:
            result["hallucination"] = "hallucination" in response_lower and "no hallucination" not in response_lower
        
        # Extract score
        if "score" in schema_class.__fields__:
            import re
            score_match = re.search(r'score[:\s]*(\d)', response_lower)
            result["score"] = int(score_match.group(1)) if score_match else 3
        
        return result
    
    def evaluate_correctness(self, question: str, student_answer: str, ground_truth: str) -> Dict:
        """Evaluate answer correctness against ground truth"""
        prompt = f"""
{CORRECTNESS_INSTRUCTIONS}

QUESTION: {question}
GROUND TRUTH ANSWER: {ground_truth}
STUDENT ANSWER: {student_answer}

Provide your evaluation in this JSON format:
{{
    "explanation": "Your detailed reasoning here",
    "correct": true/false
}}
"""
        
        try:
            response = self.llm.invoke(prompt)
            result = self._parse_structured_output(response.content, CorrectnessGrade)
            logger.info(f"Correctness evaluation completed: {result['correct']}")
            return result
        except Exception as e:
            logger.error(f"Error in correctness evaluation: {e}")
            return {"explanation": f"Evaluation error: {e}", "correct": False}
    
    def evaluate_relevance(self, question: str, answer: str) -> Dict:
        """Evaluate how well the answer addresses the question"""
        prompt = f"""
{RELEVANCE_INSTRUCTIONS}

QUESTION: {question}
ANSWER: {answer}

Provide your evaluation in this JSON format:
{{
    "explanation": "Your detailed reasoning here",
    "relevant": true/false,
    "score": 1-5
}}
"""
        
        try:
            response = self.llm.invoke(prompt)
            result = self._parse_structured_output(response.content, RelevanceGrade)
            logger.info(f"Relevance evaluation completed: {result['score']}/5")
            return result
        except Exception as e:
            logger.error(f"Error in relevance evaluation: {e}")
            return {"explanation": f"Evaluation error: {e}", "relevant": False, "score": 1}
    
    def evaluate_groundedness(self, answer: str, context: List[str]) -> Dict:
        """Evaluate if the answer is grounded in the retrieved context"""
        context_text = "\n\n".join([f"Document {i+1}: {doc}" for i, doc in enumerate(context)])
        
        prompt = f"""
{GROUNDEDNESS_INSTRUCTIONS}

RETRIEVED CONTEXT:
{context_text}

GENERATED ANSWER: {answer}

Provide your evaluation in this JSON format:
{{
    "explanation": "Your detailed reasoning here",
    "grounded": true/false,
    "hallucination": true/false
}}
"""
        
        try:
            response = self.llm.invoke(prompt)
            result = self._parse_structured_output(response.content, GroundednessGrade)
            logger.info(f"Groundedness evaluation completed: grounded={result['grounded']}, hallucination={result['hallucination']}")
            return result
        except Exception as e:
            logger.error(f"Error in groundedness evaluation: {e}")
            return {"explanation": f"Evaluation error: {e}", "grounded": False, "hallucination": True}
    
    def evaluate_retrieval_relevance(self, question: str, retrieved_docs: List[str]) -> Dict:
        """Evaluate relevance of retrieved documents to the question"""
        docs_text = "\n\n".join([f"Document {i+1}: {doc}" for i, doc in enumerate(retrieved_docs)])
        
        prompt = f"""
{RETRIEVAL_RELEVANCE_INSTRUCTIONS}

QUESTION: {question}

RETRIEVED DOCUMENTS:
{docs_text}

Provide your evaluation in this JSON format:
{{
    "explanation": "Your detailed reasoning here",
    "relevant": true/false,
    "score": 1-5
}}
"""
        
        try:
            response = self.llm.invoke(prompt)
            result = self._parse_structured_output(response.content, RetrievalRelevanceGrade)
            logger.info(f"Retrieval relevance evaluation completed: {result['score']}/5")
            return result
        except Exception as e:
            logger.error(f"Error in retrieval relevance evaluation: {e}")
            return {"explanation": f"Evaluation error: {e}", "relevant": False, "score": 1}
    
    def evaluate_complete_rag(self, question: str, answer: str, context: List[str], 
                             ground_truth: Optional[str] = None) -> Dict:
        """Perform complete RAG evaluation with all metrics"""
        results = {}
        
        # Always evaluate these three
        results["relevance"] = self.evaluate_relevance(question, answer)
        results["groundedness"] = self.evaluate_groundedness(answer, context)
        results["retrieval_relevance"] = self.evaluate_retrieval_relevance(question, context)
        
        # Only evaluate correctness if ground truth is provided
        if ground_truth:
            results["correctness"] = self.evaluate_correctness(question, answer, ground_truth)
        
        # Calculate overall score
        scores = []
        if ground_truth and "correctness" in results:
            scores.append(5 if results["correctness"]["correct"] else 1)
        scores.append(results["relevance"]["score"])
        scores.append(5 if results["groundedness"]["grounded"] else 1)
        scores.append(results["retrieval_relevance"]["score"])
        
        results["overall_score"] = sum(scores) / len(scores)
        results["summary"] = {
            "total_evaluations": len(scores),
            "has_ground_truth": ground_truth is not None,
            "overall_score": results["overall_score"]
        }
        
        logger.info(f"Complete RAG evaluation finished. Overall score: {results['overall_score']:.2f}/5")
        return results

# Example usage and testing
def test_evaluator():
    """Test the RAG evaluator with sample data"""
    evaluator = RAGEvaluator()
    
    # Sample data
    question = "What is the capital of France?"
    answer = "The capital of France is Paris. It is located in the north-central part of the country."
    ground_truth = "Paris is the capital of France."
    context = [
        "Paris is the capital and most populous city of France.",
        "Located in northern France, Paris is known for its culture and history.",
        "The city has been the capital since the 12th century."
    ]
    
    # Test individual evaluations
    print("=== Testing Individual Evaluations ===")
    
    correctness_result = evaluator.evaluate_correctness(question, answer, ground_truth)
    print(f"Correctness: {correctness_result}")
    
    relevance_result = evaluator.evaluate_relevance(question, answer)
    print(f"Relevance: {relevance_result}")
    
    groundedness_result = evaluator.evaluate_groundedness(answer, context)
    print(f"Groundedness: {groundedness_result}")
    
    retrieval_result = evaluator.evaluate_retrieval_relevance(question, context)
    print(f"Retrieval Relevance: {retrieval_result}")
    
    # Test complete evaluation
    print("\n=== Testing Complete RAG Evaluation ===")
    complete_result = evaluator.evaluate_complete_rag(question, answer, context, ground_truth)
    print(f"Complete Evaluation: {json.dumps(complete_result, indent=2)}")

if __name__ == "__main__":
    test_evaluator()