/**
 * Faculty Dashboard Page
 * Main dashboard for faculty
 */

import React from 'react';
import AppLayout from '../layouts/AppLayout.jsx';
import { Card } from '../components/Common.jsx';
import { Users, BookOpen, CheckCircle2, TrendingUp } from 'lucide-react';
import { Button } from '../components/Button.jsx';

export const FacultyDashboard = () => {
  const stats = [
    {
      title: 'Assessments',
      value: '12',
      icon: BookOpen,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100 dark:bg-blue-900',
    },
    {
      title: 'Students',
      value: '250',
      icon: Users,
      color: 'text-green-600',
      bgColor: 'bg-green-100 dark:bg-green-900',
    },
    {
      title: 'Submissions',
      value: '450',
      icon: CheckCircle2,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100 dark:bg-purple-900',
    },
    {
      title: 'Avg Pass Rate',
      value: '78%',
      icon: TrendingUp,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100 dark:bg-orange-900',
    },
  ];

  return (
    <AppLayout>
      <div className="p-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50 mb-2">
            Faculty Dashboard
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Manage your assessments and track student progress
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

        {/* Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Assessments */}
          <div className="lg:col-span-2">
            <Card className="mb-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
                  Recent Assessments
                </h2>
                <Button variant="primary" size="sm">
                  New Assessment
                </Button>
              </div>

              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="p-4 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-medium text-slate-900 dark:text-slate-50">
                          Assessment {i}
                        </h3>
                        <p className="text-sm text-slate-600 dark:text-slate-400">
                          {50 + i * 20} submissions • Created 2 days ago
                        </p>
                      </div>
                      <Button variant="ghost" size="sm">
                        View Details
                      </Button>
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
                Create Assessment
              </Button>
              <Button variant="secondary" fullWidth>
                Add Questions
              </Button>
              <Button variant="secondary" fullWidth>
                View Results
              </Button>
              <Button variant="ghost" fullWidth>
                Export Data
              </Button>
            </div>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
};

export default FacultyDashboard;
