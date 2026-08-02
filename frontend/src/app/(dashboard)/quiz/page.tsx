'use client'

import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { api } from '@/lib/api'
import {
  GraduationCap,
  Loader2,
  Sparkles,
  CheckCircle2,
  XCircle,
  Trophy,
  RefreshCw,
  Trash2,
  Clock,
  BookOpen,
  Target,
  ChevronRight,
  AlertCircle,
  Brain,
  ListChecks,
  BarChart3,
  Plus,
  FileQuestion,
} from 'lucide-react'

// ── Types ──────────────────────────────────────────────────────────────

interface Question {
  question: string
  options: Array<{ label: string; text: string }>
}

interface HistoryItem {
  id: string
  topic: string
  difficulty: string
  score: number | null
  total_questions: number
  completed: boolean
  created_at: string
}

interface Result {
  question_index: number
  question: string
  options: Array<{ label: string; text: string }>
  correct_answer: string
  explanation: string
  user_answer: string | null
  is_correct: boolean | null
}

type Phase = 'idle' | 'generating' | 'answering' | 'submitting' | 'results'

// ── Helper ─────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return 'Unknown date'
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return iso
  }
}

function getDifficultyColor(d: string) {
  switch (d) {
    case 'beginner': return 'text-emerald-500'
    case 'intermediate': return 'text-amber-500'
    case 'advanced': return 'text-rose-500'
    default: return 'text-muted-foreground'
  }
}

function getScoreColor(pct: number) {
  if (pct >= 80) return 'text-emerald-500'
  if (pct >= 60) return 'text-amber-500'
  return 'text-rose-500'
}

// ── Page Component ─────────────────────────────────────────────────────

export default function QuizPage() {
  const [phase, setPhase] = useState<Phase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)

  // Generation form
  const [topic, setTopic] = useState('')
  const [difficulty, setDifficulty] = useState('intermediate')
  const [questionCount, setQuestionCount] = useState('5')
  const [bloomsLevel, setBloomsLevel] = useState('all')

  // Active quiz
  const [quizId, setQuizId] = useState<string | null>(null)
  const [questions, setQuestions] = useState<Question[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, string>>({})
  const [checkedAnswers, setCheckedAnswers] = useState<Record<number, { is_correct: boolean; correct_answer: string; explanation: string }>>({})
  const [checkingIndex, setCheckingIndex] = useState<number | null>(null)

  // Results
  const [results, setResults] = useState<Result[] | null>(null)
  const [score, setScore] = useState(0)
  const [percentage, setPercentage] = useState(0)

  // History
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [loadingHistory, setLoadingHistory] = useState(true)

  // ── Fetch history ──────────────────────────────────────────────────

  const fetchHistory = useCallback(async () => {
    setLoadingHistory(true)
    try {
      const res = await api.quiz.history()
      if (res.success && res.data) {
        setHistory(res.data)
      } else {
        console.warn('Failed to load quiz history:', res.error)
      }
    } catch {
      console.error('Failed to load quiz history')
    } finally {
      setLoadingHistory(false)
    }
  }, [])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  // ── Generate Quiz ──────────────────────────────────────────────────

  const handleGenerate = async () => {
    if (!topic.trim()) return

    setGenerating(true)
    setError(null)
    setPhase('generating')
    setQuizId(null)
    setQuestions([])
    setCurrentIndex(0)
    setSelectedAnswers({})
    setCheckedAnswers({})
    setResults(null)

    try {
      const count = Math.min(Math.max(parseInt(questionCount, 10) || 5, 1), 20)
      const res = await api.quiz.generate({ topic: topic.trim(), difficulty, question_count: count })
      if (res.success && res.data) {
        setQuizId(res.data.quiz_id)
        setQuestions(res.data.questions)
        setPhase('answering')
      } else {
        setError(res.error || 'Failed to generate quiz')
        setPhase('idle')
      }
    } catch (e) {
      setError('Failed to generate quiz. Ensure the backend is running.')
      setPhase('idle')
    } finally {
      setGenerating(false)
    }
  }

  // ── Check Answer ───────────────────────────────────────────────────

  const handleSelectAnswer = async (label: string) => {
    if (!quizId || checkingIndex !== null) return

    const idx = currentIndex
    setSelectedAnswers((prev) => ({ ...prev, [idx]: label }))
    setCheckingIndex(idx)

    try {
      const res = await api.quiz.check({ quiz_id: quizId, question_index: idx, selected_answer: label })
      if (res.success && res.data) {
        setCheckedAnswers((prev) => ({
          ...prev,
          [idx]: {
            is_correct: res.data!.is_correct,
            correct_answer: res.data!.correct_answer,
            explanation: res.data!.explanation,
          },
        }))
      }
    } catch {
      // keep answer selected but show no feedback
    } finally {
      setCheckingIndex(null)
    }
  }

  // ── Navigation ─────────────────────────────────────────────────────

  const currentQuestion = questions[currentIndex]
  const currentChecked = checkedAnswers[currentIndex]
  const allAnswered = questions.length > 0 && questions.every((_, i) => selectedAnswers[i] !== undefined)

  const goNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((i) => i + 1)
    }
  }

  const goPrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex((i) => i - 1)
    }
  }

  // ── Submit Quiz ────────────────────────────────────────────────────

  const handleSubmit = async () => {
    if (!quizId) return
    setPhase('submitting')

    try {
      const res = await api.quiz.submit(quizId)
      if (res.success && res.data) {
        setResults(res.data.results)
        setScore(res.data.score)
        setPercentage(res.data.percentage)
        setPhase('results')
        fetchHistory()
      } else {
        setError(res.error || 'Failed to submit quiz')
        setPhase('answering')
      }
    } catch {
      setError('Failed to submit quiz')
      setPhase('answering')
    }
  }

  // ── Reset / New Quiz ───────────────────────────────────────────────

  const handleReset = () => {
    setPhase('idle')
    setQuizId(null)
    setQuestions([])
    setError(null)
    setCurrentIndex(0)
    setSelectedAnswers({})
    setCheckedAnswers({})
    setResults(null)
    setScore(0)
    setPercentage(0)
  }

  const handleLoadHistory = async (id: string) => {
    try {
      const res = await api.quiz.get(id)
      if (res.success && res.data) {
        const data = res.data
        setQuizId(data.id)
        setTopic(data.topic)
        setDifficulty(data.difficulty)
        setQuestionCount(String(data.total_questions))

        if (data.completed && data.score !== null) {
          // Load completed quiz results
          setQuestions(data.questions.map((q) => ({
            question: q.question,
            options: q.options,
          })))
          setPhase('results')
          setScore(data.score)
          setPercentage(data.total_questions > 0 ? Math.round((data.score / data.total_questions) * 100) : 0)

          // Reconstruct results
          const loadedResults: Result[] = data.questions.map((q, i) => {
            const ans = data.answers.find((a) => a.question_index === i)
            return {
              question_index: i,
              question: q.question,
              options: q.options,
              correct_answer: q.correct_answer || '',
              explanation: q.explanation || '',
              user_answer: ans?.selected_answer || null,
              is_correct: ans?.is_correct ?? null,
            }
          })
          setResults(loadedResults)
        } else {
          // Load in-progress quiz
          setQuestions(data.questions.map((q) => ({
            question: q.question,
            options: q.options,
          })))
          const restoredAnswers: Record<number, string> = {}
          const restoredChecked: Record<number, { is_correct: boolean; correct_answer: string; explanation: string }> = {}
          data.answers.forEach((a) => {
            restoredAnswers[a.question_index] = a.selected_answer
            const q = data.questions[a.question_index]
            if (q) {
              restoredChecked[a.question_index] = {
                is_correct: a.is_correct,
                correct_answer: q.correct_answer || '',
                explanation: q.explanation || '',
              }
            }
          })
          setSelectedAnswers(restoredAnswers)
          setCheckedAnswers(restoredChecked)
          setCurrentIndex(0)
          setPhase('answering')
        }
      } else {
        setError(res.error || 'Failed to load quiz')
      }
    } catch {
      setError('Failed to load quiz')
    }
  }

  // ── Delete history item ────────────────────────────────────────────

  const handleDeleteHistory = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      const res = await api.quiz.delete(id)
      if (!res.success) {
        console.error('Failed to delete quiz history:', res.error)
        return
      }
      setHistory((prev) => prev.filter((h) => h.id !== id))
      if (quizId === id) handleReset()
    } catch {
      console.error('Failed to delete quiz history')
    }
  }

  // ── Stats ──────────────────────────────────────────────────────────

  const completedCount = history.filter((h) => h.completed).length
  const avgScore = completedCount > 0
    ? Math.round(history.filter((h) => h.completed).reduce((sum, h) => sum + (h.score ?? 0), 0) / completedCount * 10) / 10
    : 0
  const avgPct = completedCount > 0
    ? Math.round(history.filter((h) => h.completed).reduce((sum, h) => {
        const pct = h.total_questions > 0 ? (h.score ?? 0) / h.total_questions * 100 : 0
        return sum + pct
      }, 0) / completedCount)
    : 0

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <div className="flex h-[calc(100vh-112px)] gap-6 animate-fade-in">
      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Quiz</h1>
            <p className="text-muted-foreground mt-1">
              Generate multiple-choice quizzes on any topic
            </p>
          </div>
          {phase !== 'idle' && (
            <Button variant="outline" className="gap-2" onClick={handleReset}>
              <RefreshCw className="h-4 w-4" />
              New Quiz
            </Button>
          )}
        </div>

        {error && (
          <div className="bg-destructive/10 text-destructive text-sm px-4 py-3 rounded-lg mb-4 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span className="flex-1">{error}</span>
            <Button variant="link" size="sm" className="h-auto p-0 text-destructive" onClick={() => setError(null)}>
              Dismiss
            </Button>
          </div>
        )}

        {/* ── IDLE: Input form ── */}
        {phase === 'idle' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Brain className="h-5 w-5 text-primary" />
                Create a New Quiz
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="space-y-2">
                <label className="text-sm font-medium">Topic</label>
                <div className="relative">
                  <BookOpen className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="e.g. Machine Learning, World History, Python..."
                    className="pl-10"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Difficulty</label>
                  <Select value={difficulty} onValueChange={setDifficulty}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="beginner">Beginner</SelectItem>
                      <SelectItem value="intermediate">Intermediate</SelectItem>
                      <SelectItem value="advanced">Advanced</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Bloom&apos;s Taxonomy</label>
                  <Select value={bloomsLevel} onValueChange={setBloomsLevel}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Cognitive Levels</SelectItem>
                      <SelectItem value="remember">1. Remember (Facts)</SelectItem>
                      <SelectItem value="understand">2. Understand (Concepts)</SelectItem>
                      <SelectItem value="apply">3. Apply (Problem Solving)</SelectItem>
                      <SelectItem value="analyze">4. Analyze (Trade-offs)</SelectItem>
                      <SelectItem value="evaluate">5. Evaluate (Critique)</SelectItem>
                      <SelectItem value="create">6. Create (Synthesis)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Questions</label>
                  <Select value={questionCount} onValueChange={setQuestionCount}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {[3, 5, 10, 15, 20].map((n) => (
                        <SelectItem key={n} value={String(n)}>{n} questions</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Button
                className="w-full gap-2 h-12 text-base"
                onClick={handleGenerate}
                disabled={!topic.trim() || generating}
              >
                {generating ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Sparkles className="h-5 w-5" />
                )}
                {generating ? 'Generating...' : 'Generate Quiz'}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* ── GENERATING: Loading state ── */}
        {phase === 'generating' && (
          <Card>
            <CardContent className="py-16">
              <div className="text-center space-y-4">
                <div className="relative mx-auto w-16 h-16">
                  <div className="absolute inset-0 rounded-full border-4 border-muted" />
                  <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-primary animate-spin" />
                  <Brain className="absolute inset-0 m-auto h-6 w-6 text-primary" />
                </div>
                <div>
                  <p className="text-lg font-medium">Generating your quiz...</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Creating {questionCount} {difficulty} questions about &ldquo;{topic}&rdquo;
                  </p>
                </div>
                <Loader2 className="mx-auto h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
        )}

        {/* ── ANSWERING: Show questions ── */}
        {phase === 'answering' && currentQuestion && (
          <div className="flex-1 flex flex-col space-y-4">
            {/* Progress bar */}
            <div className="flex items-center gap-3">
              <div className="flex-1 h-2 bg-secondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-500 rounded-full"
                  style={{ width: `${((Object.keys(checkedAnswers).length) / questions.length) * 100}%` }}
                />
              </div>
              <span className="text-sm text-muted-foreground shrink-0 tabular-nums">
                {Object.keys(checkedAnswers).length}/{questions.length} answered
              </span>
            </div>

            {/* Question card */}
            <Card className="flex-1">
              <CardContent className="p-6 space-y-6">
                <div className="flex items-center justify-between">
                  <Badge variant="outline" className="text-xs gap-1">
                    <FileQuestion className="h-3 w-3" />
                    Question {currentIndex + 1} of {questions.length}
                  </Badge>
                  <div className="flex gap-1">
                    {questions.map((_, i) => (
                      <button
                        key={i}
                        className={`w-2.5 h-2.5 rounded-full transition-all ${
                          i === currentIndex
                            ? 'bg-primary scale-125'
                            : checkedAnswers[i]
                              ? checkedAnswers[i].is_correct
                                ? 'bg-emerald-500'
                                : 'bg-rose-500'
                              : selectedAnswers[i]
                                ? 'bg-muted-foreground/40'
                                : 'bg-secondary'
                        }`}
                        onClick={() => setCurrentIndex(i)}
                      />
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold leading-relaxed">
                    {currentQuestion.question}
                  </h3>
                </div>

                {/* Options */}
                <div className="space-y-3">
                  {currentQuestion.options.map((opt) => {
                    const isSelected = selectedAnswers[currentIndex] === opt.label
                    const isChecked = checkedAnswers[currentIndex]
                    const isCorrectOpt = isChecked && opt.label === isChecked.correct_answer
                    const isWrongOpt = isChecked && isSelected && !isChecked.is_correct

                    let borderClass = 'border hover:border-primary/50 hover:bg-accent/50'
                    let bgClass = 'hover:bg-accent/50'
                    let icon = null

                    if (isChecked) {
                      if (isCorrectOpt) {
                        borderClass = 'border-emerald-500/50 bg-emerald-500/5'
                        bgClass = 'bg-emerald-500/5'
                        icon = <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" />
                      } else if (isWrongOpt) {
                        borderClass = 'border-rose-500/50 bg-rose-500/5'
                        bgClass = 'bg-rose-500/5'
                        icon = <XCircle className="h-5 w-5 text-rose-500 shrink-0" />
                      } else if (opt.label === isChecked.correct_answer) {
                        // Show correct answer when user got it wrong
                        borderClass = 'border-emerald-500/30 bg-emerald-500/5'
                        bgClass = 'bg-emerald-500/5'
                        icon = <CheckCircle2 className="h-5 w-5 text-emerald-500/60 shrink-0" />
                      }
                    } else if (isSelected) {
                      borderClass = 'border-primary/50 bg-primary/5'
                      bgClass = 'bg-primary/5'
                    }

                    return (
                      <button
                        key={opt.label}
                        className={`w-full flex items-center gap-3 rounded-lg border p-4 text-left transition-all ${borderClass} ${bgClass} ${
                          isChecked ? 'cursor-default' : 'cursor-pointer'
                        }`}
                        onClick={() => {
                          if (!isChecked) handleSelectAnswer(opt.label)
                        }}
                        disabled={!!isChecked || checkingIndex === currentIndex}
                      >
                        <span className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-semibold shrink-0 ${
                          isChecked && isCorrectOpt
                            ? 'bg-emerald-500/20 text-emerald-600'
                            : isChecked && isWrongOpt
                              ? 'bg-rose-500/20 text-rose-600'
                              : isSelected
                                ? 'bg-primary/20 text-primary'
                                : 'bg-secondary text-muted-foreground'
                        }`}>
                          {opt.label}
                        </span>
                        <span className="flex-1 text-sm">{opt.text}</span>
                        {icon}
                        {checkingIndex === currentIndex && isSelected && (
                          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground shrink-0" />
                        )}
                      </button>
                    )
                  })}
                </div>

                {/* Explanation */}
                {currentChecked && (
                  <div className={`rounded-lg p-4 text-sm space-y-1 ${
                    currentChecked.is_correct
                      ? 'bg-emerald-500/5 border border-emerald-500/20'
                      : 'bg-rose-500/5 border border-rose-500/20'
                  }`}>
                    <div className="flex items-center gap-2 font-medium">
                      {currentChecked.is_correct ? (
                        <>
                          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                          <span className="text-emerald-600 dark:text-emerald-400">Correct!</span>
                        </>
                      ) : (
                        <>
                          <XCircle className="h-4 w-4 text-rose-500" />
                          <span className="text-rose-600 dark:text-rose-400">
                            Incorrect — Answer was {currentChecked.correct_answer}
                          </span>
                        </>
                      )}
                    </div>
                    <p className="text-muted-foreground mt-1">{currentChecked.explanation}</p>
                  </div>
                )}

                {/* Navigation */}
                <div className="flex items-center justify-between pt-2">
                  <Button
                    variant="outline"
                    onClick={goPrev}
                    disabled={currentIndex === 0}
                    className="gap-2"
                  >
                    <ChevronRight className="h-4 w-4 rotate-180" />
                    Previous
                  </Button>

                  <span className="text-xs text-muted-foreground tabular-nums">
                    Q{currentIndex + 1}/{questions.length}
                  </span>

                  {currentIndex < questions.length - 1 ? (
                    <Button onClick={goNext} className="gap-2" disabled={!selectedAnswers[currentIndex]}>
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  ) : (
                    <Button
                      onClick={handleSubmit}
                      disabled={!allAnswered}
                      className="gap-2"
                    >
                      <Trophy className="h-4 w-4" />
                      Submit
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* ── RESULTS ── */}
        {phase === 'results' && results && (
          <div className="space-y-6">
            {/* Score card */}
            <Card className="overflow-hidden">
              <div className="bg-gradient-to-br from-primary/10 via-primary/5 to-background p-8 text-center">
                <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-primary/10 mb-4">
                  <Trophy className="h-10 w-10 text-primary" />
                </div>
                <h2 className="text-3xl font-bold">{topic}</h2>
                <p className="text-muted-foreground mt-1 capitalize">{difficulty} · {questions.length} questions</p>
                <div className="flex items-center justify-center gap-6 mt-6">
                  <div className="text-center">
                    <p className={`text-4xl font-bold ${getScoreColor(percentage)}`}>{percentage}%</p>
                    <p className="text-sm text-muted-foreground mt-1">Score</p>
                  </div>
                  <div className="h-12 w-px bg-border" />
                  <div className="text-center">
                    <p className={`text-4xl font-bold ${score >= questions.length / 2 ? 'text-emerald-500' : 'text-rose-500'}`}>
                      {score}/{questions.length}
                    </p>
                    <p className="text-sm text-muted-foreground mt-1">Correct</p>
                  </div>
                  <div className="h-12 w-px bg-border" />
                  <div className="text-center">
                    <p className="text-4xl font-bold text-muted-foreground">
                      {questions.length - score}
                    </p>
                    <p className="text-sm text-muted-foreground mt-1">Incorrect</p>
                  </div>
                </div>
              </div>
            </Card>

            {/* Results list */}
            <div className="space-y-3">
              <h3 className="font-semibold flex items-center gap-2">
                <ListChecks className="h-5 w-5" />
                Detailed Results
              </h3>
              {results.map((r, i) => (
                <Card key={i} className={`border-l-4 ${r.is_correct ? 'border-l-emerald-500' : 'border-l-rose-500'}`}>
                  <CardContent className="p-4 space-y-3">
                    <div className="flex items-start gap-3">
                      {r.is_correct ? (
                        <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
                      ) : (
                        <XCircle className="h-5 w-5 text-rose-500 shrink-0 mt-0.5" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm">
                          {i + 1}. {r.question}
                        </p>
                        <div className="flex flex-wrap gap-2 mt-2">
                          {r.options.map((opt) => {
                            const isCorrectOpt = opt.label === r.correct_answer
                            const isUserOpt = opt.label === r.user_answer
                            let variant: 'default' | 'secondary' | 'outline' = 'outline'
                            let extraClass = ''

                            if (isCorrectOpt) {
                              variant = 'default'
                              extraClass = 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30 hover:bg-emerald-500/20'
                            } else if (isUserOpt && !r.is_correct) {
                              extraClass = 'bg-rose-500/10 text-rose-600 border-rose-500/30'
                            }

                            return (
                              <Badge key={opt.label} variant={variant} className={`text-xs ${extraClass}`}>
                                {opt.label}. {opt.text}
                                {isCorrectOpt && ' ✓'}
                                {isUserOpt && !isCorrectOpt && ' ✗'}
                              </Badge>
                            )
                          })}
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">{r.explanation}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            <div className="flex gap-3 justify-center">
              <Button variant="outline" className="gap-2" onClick={handleReset}>
                <RefreshCw className="h-4 w-4" />
                New Quiz
              </Button>
              <Button className="gap-2" onClick={() => {
                setTopic(topic)
                setPhase('idle')
              }}>
                <Sparkles className="h-4 w-4" />
                Generate Another
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* ── Sidebar: History & Stats ── */}
      <div className="hidden lg:block w-80 space-y-4 shrink-0">
        {/* Stats */}
        {completedCount > 0 && (
          <Card className="p-4">
            <h3 className="font-semibold flex items-center gap-2 mb-3 text-sm">
              <BarChart3 className="h-4 w-4" />
              Your Stats
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-secondary/50 rounded-lg p-3 text-center">
                <p className="text-2xl font-bold">{completedCount}</p>
                <p className="text-xs text-muted-foreground">Quizzes</p>
              </div>
              <div className="bg-secondary/50 rounded-lg p-3 text-center">
                <p className={`text-2xl font-bold ${getScoreColor(avgPct)}`}>{avgPct}%</p>
                <p className="text-xs text-muted-foreground">Avg Score</p>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-3 text-center">
              Average score: <span className="font-medium">{avgScore}/{history.filter(h => h.completed).reduce((s, h) => s + h.total_questions, 0) > 0
                ? Math.round(history.filter(h => h.completed).reduce((s, h) => s + h.total_questions, 0) / completedCount)
                : 0}</span> per quiz
            </p>
          </Card>
        )}

        {/* History */}
        <Card className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold flex items-center gap-2 text-sm">
              <Clock className="h-4 w-4" />
              History
            </h3>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs gap-1"
              onClick={handleReset}
            >
              <Plus className="h-3 w-3" />
              New
            </Button>
          </div>

          {loadingHistory ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <GraduationCap className="h-8 w-8 mx-auto mb-2 opacity-40" />
              <p className="text-xs">No quizzes yet</p>
              <p className="text-xs mt-1">Create your first quiz above</p>
            </div>
          ) : (
            <ScrollArea className="h-[calc(100vh-320px)] -mx-1">
              <div className="space-y-1 px-1">
                {history.map((item) => {
                  const pct = item.total_questions > 0 && item.score !== null
                    ? Math.round((item.score / item.total_questions) * 100)
                    : null
                  return (
                    <div
                      key={item.id}
                      className={`group flex items-start gap-2 rounded-md px-3 py-2 text-sm cursor-pointer transition-colors ${
                        item.id === quizId ? 'bg-primary/10 text-primary' : 'hover:bg-secondary'
                      }`}
                      onClick={() => handleLoadHistory(item.id)}
                    >
                      <GraduationCap className="h-4 w-4 shrink-0 mt-0.5 opacity-60" />
                      <div className="flex-1 min-w-0">
                        <p className="truncate text-xs font-medium">{item.topic}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <Badge variant="secondary" className={`text-[10px] ${getDifficultyColor(item.difficulty)}`}>
                            {item.difficulty}
                          </Badge>
                          {item.completed && pct !== null ? (
                            <span className={`text-[11px] font-medium ${getScoreColor(pct)}`}>
                              {pct}%
                            </span>
                          ) : item.completed === false ? (
                            <span className="text-[11px] text-muted-foreground">In progress</span>
                          ) : null}
                        </div>
                        <p className="text-[10px] text-muted-foreground mt-0.5">
                          {formatDate(item.created_at)}
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 shrink-0 opacity-40 hover:opacity-100 hover:text-destructive transition-opacity"
                        onClick={(e) => handleDeleteHistory(item.id, e)}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  )
                })}
              </div>
            </ScrollArea>
          )}
        </Card>

        {/* Tips */}
        <Card className="p-4">
          <h3 className="font-semibold flex items-center gap-2 mb-2 text-xs uppercase tracking-wider text-muted-foreground">
            <Target className="h-3 w-3" />
            Tips
          </h3>
          <ul className="space-y-1.5 text-xs text-muted-foreground">
            <li className="flex items-start gap-2">
              <span className="text-primary mt-0.5">•</span>
              Choose specific topics for better questions
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary mt-0.5">•</span>
              Use &ldquo;Advanced&rdquo; for deeper knowledge checks
            </li>
            <li className="flex items-start gap-2">
              <span className="text-primary mt-0.5">•</span>
              Past quizzes are saved for review
            </li>
          </ul>
        </Card>
      </div>
    </div>
  )
}
