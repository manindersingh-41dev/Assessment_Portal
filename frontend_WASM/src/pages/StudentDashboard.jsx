/**
 * Student Dashboard Page
 * Main dashboard for students
 */

import React from 'react';
import AppLayout from '../layouts/AppLayout.jsx';
import { Card } from '../components/Common.jsx';
import { BarChart3, BookOpen, CheckCircle2, Clock } from 'lucide-react';
import { Button } from '../components/Button.jsx';

export const StudentDashboard = () => {
  const stats = [
    {
      title: 'Assessments',
      value: '5',
      icon: BookOpen,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100 dark:bg-blue-900',
    },
    {
      title: 'Completed',
      value: '3',
      icon: CheckCircle2,
      color: 'text-green-600',
      bgColor: 'bg-green-100 dark:bg-green-900',
    },
    {
      title: 'In Progress',
      value: '1',
      icon: Clock,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-100 dark:bg-yellow-900',
    },
    {
      title: 'Average Score',
      value: '87%',
      icon: BarChart3,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100 dark:bg-purple-900',
    },
  ];

  return (
    <AppLayout>
      <div className="p-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50 mb-2">
            Welcome back!
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Here's what's happening with your assessments
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat) => (
            <Card key={stat.title} className="hover:shadow-md transition-shadow">
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                  <stat.icon className={`w-6 h-6 ${stat.color}`} />
                </div>
                <div>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    {stat.title}
                  </p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-slate-50">
                    {stat.value}
                  </p>
                </div>
              </div>
            </Card>
          ))}
        </div>

        {/* Active Assessments */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Card className="mb-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
                  Active Assessments
                </h2>
                <Button variant="ghost" size="sm">
                  View All
                </Button>
              </div>

              <div className="space-y-4">
                {[1, 2].map((i) => (
                  <div
                    key={i}
                    className="p-4 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-medium text-slate-900 dark:text-slate-50">
                          Assessment {i}
                        </h3>
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                          5 questions • 120 minutes
                        </p>
                      </div>
                      <span className="px-3 py-1 rounded-full text-xs font-medium bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300">
                        In Progress
                      </span>
                    </div>
                    <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                      <div
                        className="bg-primary-600 h-2 rounded-full"
                        style={{ width: `${40 + i * 20}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Quick Actions */}
          <Card>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-50 mb-4">
              Quick Actions
            </h3>
            <div className="space-y-3">
              <Button variant="primary" fullWidth>
                Start Assessment
              </Button>
              <Button variant="secondary" fullWidth>
                View Results
              </Button>
              <Button variant="ghost" fullWidth>
                Help & Support
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
};

export default StudentDashboard;
